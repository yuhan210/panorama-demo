import redis
import pickle
import math

with open('./lib/data/video_list.txt') as fh:
    video_names = fh.read().split()

with open('../data/stream_rates.pickle') as fh:
    video_frame_rate = pickle.load(fh)    

with open('./lib/data/video_frame_num.pickle') as fh:
    video_lengths = pickle.load(fh)
 

if __name__ == "__main__":

    video_length_in_sec = {}
    for video_name in video_names:
        frame_num = video_lengths[video_name]
        video_length_in_sec[video_name] = int(math.floor(video_lengths[video_name]/video_frame_rate[video_name][0]))

    STEP = 5
    SIZE = 5
    for vid, video_name in enumerate(video_names):
        fps = int(round(video_frame_rate[video_name][0]))
        video_len_in_frames = video_lengths[video_name]

        start_ts = 0
        start_frame_num = start_ts * fps 
        while start_frame_num < video_len_in_frames:
            end_frame_num = min(start_frame_num + SIZE * fps, video_len_in_frames)
            frames = end_frame_num - start_frame_num

            out_video_name = './video-snippets/' + video_name + '_' + str(start_ts) + '.mp4'
            outstr = 'ffmpeg -framerate ' + str(fps) + ' -start_number ' + str(start_frame_num) + ' -i /home/ubuntu/frames/' + video_name + '/%d.jpg -vframes ' + str(frames) +  ' -s 560x420 -vcodec libx264 -pix_fmt yuv420p ' + out_video_name
            print outstr
            start_ts += STEP         
            start_frame_num = start_ts * fps 

