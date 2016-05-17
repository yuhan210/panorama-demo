import os
import time
import pickle
import json
import math
import datetime
import logging
import flask
from flask.ext.cors import CORS
import operator
import inflection
import werkzeug
import optparse
import tornado.wsgi
import tornado.httpserver
import numpy as np
from utils import *

VIDEOS = open('video_list.txt').read().split()
TOPK = 6
SERVER_STORAGE_FRAMES = 5 * 30

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
      import random
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
    app.search_index = SearchObject()

    if opts.debug:
        app.run(debug=True, host='0.0.0.0', port=opts.port)
    else:
        start_tornado(app, opts.port)


def init():
    
    global stream_rates
    global start_fid_set
    global stream_framenum
    global blocking_videos
    
    blocking_videos = []
    for video_name in open('blocking_videos').read().split():
	     blocking_videos += [video_name]

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
