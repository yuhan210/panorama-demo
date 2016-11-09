import os
import time
import pickle
import json
import random
import math
import datetime
import redis
import logging
import flask
from flask_cors import CORS
import operator
import inflection
import werkzeug
import optparse
import tornado.wsgi
import tornado.httpserver
import numpy as np
import heapq

TOPK = 20
NUM_UNMATCHED_VIDEOS = 30
SERVER_STORAGE_FRAMES = 5 * 30
SERVER_DELAY_SECS = 5
SNIPPET_FOLDER = '/var/www/html/panorama-demo/video-snippets'
SERVER_URL = 'http://ec2-54-87-87-35.compute-1.amazonaws.com'
ELMO_URL  = "http://elmo.csail.mit.edu"

random.seed(0)
# Obtain the flask app object
app = flask.Flask(__name__)
CORS(app)

#http://localhost:5000/search?query=test
@app.route('/search', methods=['GET'])
def search():

    query_str = flask.request.args.get('query','')
    rand_idx = int(flask.request.args.get('rand_idx','0'))
    logging.info('Query: %s, rand_idx: %d', query_str, rand_idx)
    search_results = app.search_index.search(query_str)

    print search_results

    return flask.jsonify(success = True, response = search_results) 


@app.route('/redis-search', methods=['GET'])
def redis_search():
    query_str = flask.request.args.get('query','')
    option = flask.request.args.get('option', 'Default')
    logging.info('Query: %s', query_str)
    cur_ts = time.time()
    search_results = app.search_handler.search(query_str, cur_ts, option)
    print search_results 

    
    return flask.jsonify(success = True, response = search_results) 

def get_videoseg_name(video_name, fid):

    n_frames = stream_framenum[video_name]

    chunk = fid / SERVER_STORAGE_FRAMES
    start_fid = chunk * SERVER_STORAGE_FRAMES
    end_fid = start_fid + SERVER_STORAGE_FRAMES

    videoseg_name = video_name + '_' + str(start_fid) + '_' + str(end_fid)  + '.mp4'

    return videoseg_name, start_fid, end_fid


def compose_response(rand_idx, opt_text_vis_ranks, opt_text_ranks, meta_ranks):

    response_dict = {}
    response_dict['opt_text_vis'] = {}
    for idx, tup in enumerate(opt_text_vis_ranks):

        stream_name = tup[0]
        p = [pos for pos, char in enumerate(stream_name) if char == '_']
        video_name = stream_name[:p[-2]]
        start_frame_fid = int(stream_name[p[-2]+1:p[-1]])
        end_frame_fid = int(stream_name[p[-1]+1:-4])
        start_time = start_frame_fid/int(stream_rates[video_name])
        end_time =  end_frame_fid/int(stream_rates[video_name])
        
        response_dict['opt_text_vis'][idx] = {'video_name': video_name, 'start_time': start_time, 'end_time': end_time, 'score': tup[1]}

    response_dict['opt_text'] = {}
    for idx, tup in enumerate(opt_text_ranks):
        stream_name = tup[0]
        p = [pos for pos, char in enumerate(stream_name) if char == '_']
        video_name = stream_name[:p[-2]]
        start_frame_fid = int(stream_name[p[-2]+1:p[-1]])
        end_frame_fid = int(stream_name[p[-1]+1:-4])
        start_time = start_frame_fid/int(stream_rates[video_name])
        end_time =  end_frame_fid/int(stream_rates[video_name])

        response_dict['opt_text'][idx] = {'video_name': video_name, 'start_time': start_time, 'end_time': end_time, 'score': tup[1]}

    response_dict['metadata'] = {}
    for idx, tup in enumerate(meta_ranks):
        video_name = tup[0]
        start_frame_fid = start_fid_set[rand_idx][video_name] 
        stream_name, start_fid, end_fid = get_videoseg_name(video_name, start_frame_fid)
        start_time = start_fid/int(stream_rates[video_name])
        end_time =  end_fid/int(stream_rates[video_name])

        response_dict['metadata'][idx] = {'video_name': video_name, 'start_time': start_time, 'end_time': end_time, 'score': tup[1]}

    return response_dict


@app.route('/')
def index():
    return flask.render_template('index.html', has_result=False)


class SearchHandler:
    def __init__(self): 
        self.start_ts = time.time() - 10
        self._redis = redis.StrictRedis()

        with open('../data/video_list.txt') as fh:
            self.video_names = fh.read().split()
        with open('../data/stream_rates.pickle') as fh:
            self.video_frame_rate = pickle.load(fh)
        with open('../data/video_frame_num.pickle') as fh:
            self.video_length_in_frames = pickle.load(fh)

        self.video_length_in_secs = {}
        for video_name in self.video_names:
            self.video_length_in_secs[video_name] = self.video_length_in_frames[video_name]/int(round(self.video_frame_rate[video_name][0]))

    def get_matching_prec(self, obj_tags, query_list):
        num_matching_query = 0
        for query in query_list:
            if query in obj_tags:
                num_matching_query += 1

        return num_matching_query/float(len(query_list))

    def get_vis_score(self, query, vis_features, video_name):

        MS_W = -0.4
        DT_W = 0.2
        SIZE_W = 0.8
        vis_features['dwell_time'] /= (self.video_frame_rate[video_name][0] * 5) 
        print vis_features
        
        score = MS_W * vis_features['moving_speed'] + DT_W * vis_features['dwell_time']/ + SIZE_W * vis_features['size']
        if math.isnan(score): 
            return 0
        return score

    def get_relevance_score(self, query_list, feature_dict, video_name):
        obj_tags = feature_dict['obj_tags']   
        vis_features = feature_dict['obj_vis_features']
        
        # text score
        text_score = self.get_matching_prec(obj_tags, query_list) 

        # vis score
        query_score = {}
        for query in query_list:  
            if query in vis_features:
                vis_score = self.get_vis_score(query, vis_features[query], video_name)
                query_score[query] = vis_score
            else:
                query_score[query] = 0
          
        print 'query_score:', query_score, 'text:', text_score
        final_score = 0.7 * text_score + 0.3 * max([query_score[x] for x in query_score])

        check_ws = ['bear', 'goat', 'sheep', 'tiger', 'dog', 'cat']
        for w in check_ws:
            if video_name.find(w) >= 0 and w not in query_list:   
                final_score = 0 
             
        return final_score

    def sort_streams(self, ts, query_list, relevant_streams):
        # sid to video_name
        stream_scores = {}
        for vid in relevant_streams:
            feature_table_key = str(ts)  + ':' + str(vid)
            feature_pickle = self._redis.get(feature_table_key) 
            feature_dict = pickle.loads(feature_pickle)
            score = self.get_relevance_score(query_list, feature_dict, self.video_names[int(vid)])
            stream_scores[self.video_names[int(vid)]] = score
        return sorted(stream_scores.items(), key=lambda x: x[1], reverse = True)

    def get_unmatched_videos(self, ts, relevant_vids, unmatched_k = NUM_UNMATCHED_VIDEOS):
        unmatched_videos = []
        n = 0
        for sid, video_name in enumerate(self.video_names):
            remaining_time = self.video_length_in_secs[video_name] - ts
            if remaining_time > SERVER_DELAY_SECS and sid not in relevant_vids:            
                # Reservoir sampling
                n += 1    
                num_selected = len(unmatched_videos) 
                if num_selected < unmatched_k:
                    unmatched_videos += [{'video_name': video_name, 'start': ts - SERVER_DELAY_SECS, 'end': ts, 'score': 0,'delay': 0}] 
                else:
                    r = int(random.random() * n)
                    if r < unmatched_k:
                        unmatched_videos[r] = {'video_name': video_name, 'start': ts - SERVER_DELAY_SECS, 'end': ts, 'score': 0,'delay': 0}
        return unmatched_videos

    def search(self, query, cur_ts, option = 'Default'):

        query_list = query.split(' ')
        ts = int((cur_ts - self.start_ts) % 200.)/5 * 5

        ##
        if "dog" in query_list and "beach" in query_list:
            ts = 20
        elif "dog" in query_list and "snow" in query_list:
            ts = 20
        elif "car" in query_list and "person" in query_list:
            ts = 15
        elif "car" in query_list and "street" in query_list:
            ts = 25
        elif "car" in query_list:
            ts = 75
        elif "dog" in query_list:
            ts = 30
        elif "guitar" in query_list:
            ts = 40
        elif "turtle" in query_list:
            ts = 75
        elif "ski" in query_list:
            ts = 85
        elif "beach" in query_list:
            ts = 20
        elif "person" in query_list:
            ts = 35
        elif "sofa" in query_list:
            ts = 180
        elif "basketball" in query_list:
            ts = 195
        ## 

             
        reverse_table_keys = [str(ts) + ':' + str(query) for query in query_list]
        relevant_sids = self._redis.sunion(reverse_table_keys)
        num_relevant_streams = len(list(relevant_sids))

        if option == 'Length':

            relevant_videos = [] 
            if num_relevant_streams > 0:
                video_name_length = {} 
                for sid in list(relevant_sids):
                    video_name = self.video_names[int(sid)]
                    video_name_length[video_name] = self.video_length_in_secs[video_name]

                video_name_length = sorted(video_name_length.items(), key=lambda x: x[1])
                for i in xrange(min(TOPK, num_relevant_streams)):
                    snippet_filename =  video_name_length[i][0] + '_' + str(ts-SERVER_DELAY_SECS) + '.mp4'
                    snippet_path = os.path.join(SNIPPET_FOLDER, snippet_filename)  
 
                    if os.path.exists(snippet_path):
                        video_url = SERVER_URL + '/panorama-demo/video-snippets/' + snippet_filename 
                    else:
                        video_url = ELMO_URL + '/panorama-demo/videos/' + video_name_length[i][0] + '.mp4#t=' + str(ts-SERVER_DELAY_SECS)

                    relevant_videos += [{'video_name': video_name_length[i][0], 'start': ts - SERVER_DELAY_SECS, 'end': ts, 'score' : video_name_length[i][1],'delay': 0, 'video_url':video_url}] 

            unmatched_videos = []
            video_name_length = {}
            for sid, video_name in enumerate(self.video_names):
                if sid not in list(relevant_sids):
                    video_name = self.video_names[sid]
                    video_name_length[video_name] = self.video_length_in_secs[video_name]
        
            video_name_length = sorted(video_name_length.items(), key=lambda x: x[1])
            for i in xrange(min(NUM_UNMATCHED_VIDEOS, len(video_name_length))):
                    snippet_filename =  video_name_length[i][0] + '_' + str(ts-SERVER_DELAY_SECS) + '.mp4'
                    snippet_path = os.path.join(SNIPPET_FOLDER, snippet_filename)  
 
                    if os.path.exists(snippet_path):
                        video_url = SERVER_URL + '/panorama-demo/video-snippets/' + snippet_filename 
                    else:
                        video_url = ELMO_URL + '/panorama-demo/videos/' + video_name_length[i][0] + '.mp4#t=' + str(ts-SERVER_DELAY_SECS)

                    unmatched_videos += [{'video_name': video_name_length[i][0], 'start': ts - SERVER_DELAY_SECS, 'end': ts, 'score' : video_name_length[i][1],'delay': 0, 'video_url': video_url}] 
             
        elif option == 'Default':
        
            relevant_videos = []
            if num_relevant_streams > 0:
                stream_scores = self.sort_streams(ts, query_list, list(relevant_sids))

                print stream_scores 
                # randomly select TOPK streams
                for i in xrange(min(TOPK, num_relevant_streams)):
                    score = stream_scores[i][1]
                    video_name = stream_scores[i][0]

                    snippet_filename =  video_name + '_' + str(ts-SERVER_DELAY_SECS) + '.mp4'
                    snippet_path = os.path.join(SNIPPET_FOLDER, snippet_filename)  
 
                    if os.path.exists(snippet_path):
                        video_url = SERVER_URL + '/panorama-demo/video-snippets/' + snippet_filename 
                    else:
                        video_url = ELMO_URL + '/panorama-demo/videos/' + video_name + '.mp4#t=' + str(ts-SERVER_DELAY_SECS)
                    #relevant_videos += [{'video_name': video_name, 'start': ts - SERVER_DELAY_SECS, 'end': ts, 'score' : (-1) * score,'delay': random.randint(0, 5)}] 
                    relevant_videos += [{'video_name': video_name, 'start': ts - SERVER_DELAY_SECS, 'end': ts, 'score' : score,'delay': 0, 'video_url':video_url}] 

            unmatched_videos = []
            video_name_length = {}
            for sid, video_name in enumerate(self.video_names):
                if sid not in list(relevant_sids):
                    video_name = self.video_names[sid]
                    video_name_length[video_name] = self.video_length_in_secs[video_name]
        
            video_name_length = sorted(video_name_length.items(), key=lambda x: x[1])[3:]
            for i in xrange(min(NUM_UNMATCHED_VIDEOS, len(video_name_length))):
                    snippet_filename =  video_name_length[i][0] + '_' + str(ts-SERVER_DELAY_SECS) + '.mp4'
                    snippet_path = os.path.join(SNIPPET_FOLDER, snippet_filename)  
 
                    if os.path.exists(snippet_path):
                        video_url = SERVER_URL + '/panorama-demo/video-snippets/' + snippet_filename 
                    else:
                        video_url = ELMO_URL + '/panorama-demo/videos/' + video_name_length[i][0] + '.mp4#t=' + str(ts-SERVER_DELAY_SECS)
                    unmatched_videos += [{'video_name': video_name_length[i][0], 'start': ts - SERVER_DELAY_SECS, 'end': ts, 'score' : video_name_length[i][1],'delay': 0, 'video_url': video_url}] 
             
            #unmatched_videos = self.get_unmatched_videos(ts, list(relevant_sids))  

        return {'relevant': relevant_videos, 'irrelevant': unmatched_videos} 
 
class SearchObject:

  def __init__(self):
    with open('../data/index.pickle') as fh:
      self.index = pickle.load(fh)
    self.prepared_index = None
    self.prepare()

  def prepare(self):

    self.video_names = self.index['dog'].keys()
    self.prepared_index = {}
    for keyword in self.index.keys():
      sorted_index = sorted(self.index[keyword].items(), key = lambda x: x[1]['score'], reverse = True)    
      irrelevant_videos =  [x for x in sorted_index if x[1]['score'] < 0.00001]
      irrelevant_videos = irrelevant_videos[: min(TOPK, len(irrelevant_videos))]
      match_videos =  [x for x in sorted_index if x[1]['score'] > 0.2 and x[0].find('capital_cities__kangaroo_court_forever_kid_remix_p_Xv0mmPZJE') < 0 and x[0].find('adorable_baby_lambs_5EbATpgZEMw') < 0]
      # select topk video for streaming
      random.seed(0)
      relevant_videos = match_videos[:TOPK]
      #relevant_videos = random.sample(match_videos[2:], min(max(0, TOPK - 2), len(match_videos[2:])))
    
      sorted_relevant_videos = [] 
      sorted_irrelevant_videos = []
      for item in relevant_videos:
        video_name = item[0]
    
        video_info = item[1]
        sorted_relevant_videos += [{'video_name': video_name, 'start': video_info['video_start']/stream_rates[video_name], 'end': video_info['video_end']/stream_rates[video_name], 'score': video_info['score'], 'delay': random.randint(0, 10)}] 

      for item in irrelevant_videos:    
        video_name = item[0]
        video_info = item[1]
        sorted_irrelevant_videos += [{'video_name': video_name, 'start': video_info['video_start']/stream_rates[video_name], 'end': video_info['video_end']/stream_rates[video_name], 'score': video_info['score'], 'delay': random.randint(0, 10)}] 
 
      self.prepared_index[keyword] = {'relevant': sorted_relevant_videos, 'irrelevant': sorted_irrelevant_videos} 

  def search(self, keyword):
      return self.prepared_index[keyword]
             
def start_tornado(app, port=5000):

    http_server = tornado.httpserver.HTTPServer(
        tornado.wsgi.WSGIContainer(app))
    http_server.listen(port)
    print("Tornado server starting on port {}".format(port))
    tornado.ioloop.IOLoop.instance().start()


def start_from_terminal(app):

    """
    Parse command line options and start the server.
    """
    parser = optparse.OptionParser()
    parser.add_option(
        '-d', '--debug',
        help="enable debug mode",
        action="store_true", default=False)
    parser.add_option(
        '-p', '--port',
        help="which port to serve content on",
        type='int', default=5000)

    opts, args = parser.parse_args()

    # load index
    # app.search_index = SearchObject()

    app.search_handler = SearchHandler()

    if opts.debug:
        app.run(debug=True, host='0.0.0.0', port=opts.port)
    else:
        start_tornado(app, opts.port)


def get_shortened_video():  
    queries = ['dog beach','dog snow', 'car person', 'car street', 'car', 'dog', 'guitar', 'turtle', 'ski', 'beach', 'person', 'sofa']  
    h = SearchHandler()
    fh = open('log', 'w')
    for query in queries:
        h = SearchHandler()
        results = h.search(query, 123)
        for rank, x in enumerate(results['relevant']):
            if rank == 10:
                break

            fh.write(x['video_name'] + ' ' + str(x['start']) + '\n')
    fh.close()

def init():
    
    global stream_rates
    global start_fid_set
    global stream_framenum

    with open('stream_rates.pickle') as fh:
        data = pickle.load(fh)
    stream_rates = {} 
    for video_name in data.keys():
        stream_rates[video_name] = data[video_name][0]

    with open('video_frame_num.pickle') as fh:
        stream_framenum = pickle.load(fh)


if __name__ == '__main__':
    init()
    logging.getLogger().setLevel(logging.INFO)
    start_from_terminal(app)
    #get_shortened_video()
