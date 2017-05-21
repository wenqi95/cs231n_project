import numpy as np
from tqdm import tqdm
import glob
import os
import gc
import multiprocessing as mp

# image
from scipy.misc import imread, imsave
from PIL import Image
from moviepy.editor import VideoFileClip
from skimage import img_as_float

# CNN model
from keras.applications.vgg16 import VGG16
from keras.applications.vgg16 import preprocess_input

def load_features(num_videos, num_frames, h, w, c, skip_num=0):
    '''
    Concanate video frames over short clip period
    frame_dir: frames folder directory
    num_videos: how many videos needed
    '''
    batch_size = 64
    model = vgg_16_pretrained()

    labels = np.load(os.getcwd() + '/datasets/category.npy')
    curr = os.getcwd()
    cache_path = os.path.join(curr, 'datasets', 'cache',
                              'num_videos{0}_skipnum{1}_num_frame{2}.npz'.format(num_videos, skip_num, num_frames))

    # initialize cache dir
    if not os.path.exists(os.path.join(curr, 'datasets', 'cache')):
        os.makedirs(os.path.join(curr, 'datasets', 'cache'))

    if os.path.isfile(cache_path):
        print('find matched cache file {}'.format(cache_path))
        cache_data = np.load(cache_path)
        return cache_data['Xtrain'], cache_data['ytrain']

    video_info_list = []
    for i in range(skip_num, num_videos+skip_num):
        video_path = os.path.join(curr, 'datasets', 'processed', 'processed_{}.mp4'.format(labels[i, 0]))
        video_info_list.append((video_path, labels[i, 1], num_frames, h, w))

    p = mp.Pool(mp.cpu_count())
    print('processing videos...')

    Xtrain = np.zeros((num_videos, num_frames, 7, 7, 512))
    ytrain = []
    temp_frames_collection = []
    for i, frames in enumerate(p.imap(process_video, video_info_list)):
        ytrain.append(int(frames[0]))
        temp_frames_collection.append(frames[1])

        # process when accumulate 10 batches
        if (i+1) % (1 * batch_size) == 0:
            print('process {0}/{1}'.format(i+1, num_videos))
            frames = np.concatenate(temp_frames_collection, axis=0)
            frames = frames.reshape((-1, h, w, c))
            temp_Xtrain = model.predict(frames)
            temp_Xtrain = temp_Xtrain.reshape((-1, num_frames, 7, 7, 512))
            Xtrain[i+1-1*batch_size:i+1,:,:,:,:] = temp_Xtrain
            temp_frames_collection = []

    # process the remaining frames
    if len(temp_frames_collection) > 0:
        frames = np.concatenate(temp_frames_collection, axis=0)
        frames = frames.reshape((-1, h, w, c))
        temp_Xtrain = model.predict(frames)
        temp_Xtrain = temp_Xtrain.reshape((-1, num_frames, 7, 7, 512))
        Xtrain[-len(temp_frames_collection):,:,:,:,:] = temp_Xtrain
        temp_frames_collection = []

    Xtrain = np.concatenate(Xtrain)
    ytrain = np.array(ytrain)

    print('cache processed data...')
    np.savez(cache_path, Xtrain=Xtrain, ytrain=ytrain)
    
    del model
    gc.collect()
    
    return Xtrain, ytrain

def vgg_16_pretrained():
    '''
    VGG 16 pretrained model without last 3 fully-connected
    '''
    # vgg without 3 fc
    model = VGG16(weights='imagenet', include_top=False)
    for layer in model.layers:
        layer.trainable = False
    return model

def process_video(video_info):
    video_path = video_info[0]
    video_cateogory = video_info[1]
    output_frames = video_info[2]
    h = video_info[3]
    w = video_info[4]

    vidcap = VideoFileClip(video_path)
    tot_count = int(vidcap.fps * vidcap.duration)

    output_interval = tot_count // output_frames
    count, frame_count = 0, 0

    video_selected_frames = list()
    for frame in vidcap.iter_frames():
        count += 1
        if count % output_interval == 0: # per second
            # check the number of output frames
            if frame_count == output_frames: break
            frame_count += 1
            img = Image.fromarray(frame, 'RGB')
            processed_img = resize_method(img, h, w)
            video_selected_frames.append(processed_img)
    del vidcap
    return (video_cateogory, video_selected_frames)

def resize_method(im, h, w):
    im_resized = im.resize((h, w), Image.ANTIALIAS)
    im_arr = np.transpose(np.array(im_resized), (0,1,2))
    im_arr = np.expand_dims(im_resized, axis=0) # add one dimension as 1
    im_arr.flags.writeable = True
    im_arr = im_arr.astype(np.float32)
    im_arr = preprocess_input(im_arr)
    return im_arr

if __name__ == '__main__':
    # testing purpose
    Xtrain, ytrain = load_features(num_videos=2, num_frames=11, h=224, w=224, c=3)
    print(Xtrain.shape)
    print(ytrain.shape)