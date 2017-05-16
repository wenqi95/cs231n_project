# !usr/env python 3.5

# import module
from keras.applications.vgg16 import VGG16
from keras.applications.vgg16 import preprocess_input
from keras.layers import Dense, Activation
from keras.layers import Input, Flatten, Dense
from keras.models import Model
from keras import optimizers
from keras.layers.pooling import MaxPooling3D
from keras.layers.core import Flatten
from keras.layers.core import Dropout
from keras import regularizers

import cv2
from scipy.misc import imread, imsave
from skimage import img_as_float
from PIL import Image
from sklearn.externals.joblib import Parallel, delayed

import multiprocessing as mp
import numpy as np
import glob
import os
from tqdm import tqdm

curr = os.getcwd()
video_dir = curr + '/datasets/frames'

'''
include_top = True: contain three fully-connected layers and
could be decoded as imagenet class
include_top = False: not contain three fully-connected

VGG16 default size 224 * 224 * 3
'''

class video_classification(object):

    def __init__(self, lr = 1e-2, reg = 0.01, name = 'VGG16', shape = (224, 224, 3)):
        self.size = shape
        self.lr = lr # learning rate
        self.reg = reg
        self.features = None
        if name == 'VGG16':
            self.model = self.vgg_16_pretrained()
        else:
            pass

    def vgg_16_pretrained(self):
        # build up model
        input = Input(shape=self.size,name = 'image_input')

        # vgg without 3 fc
        basic_vgg = VGG16(weights='imagenet', include_top=False)
        output_vgg16 = basic_vgg(input)
        my_model = basic_vgg

        return my_model

    def load_features(self, frame_dir, num_videos):
        all_data = np.zeros((num_videos, 10, 7, 7, 512)) # (#samples, #frames_per_video, h, w, c); h, w, c from vgg output
        labels = np.load(os.getcwd() + '/datasets/category.npy')

        for i in tqdm(range(0, num_videos)):
            idx = labels[i, 0]
            path = os.path.join(frame_dir, idx)

        #     if not os.path.exists(path):
        #         print('path not exists for {}'.format(idx))
        #         continue

        #     for fn in glob.glob(path+'/*.jpg'):
        #         im = Image.open(fn)
        #         # resize image
        #         h, w, c= self.size
        #         im_resized = im.resize((h, w), Image.ANTIALIAS)

        #         # transform to array
        #         im_arr = np.transpose(np.array(im_resized), (0,1,2))

        #         # preprocess image
        #         im_arr = np.expand_dims(im_arr, axis=0) # add one dimension as 1
        #         im_arr.flags.writeable = True
        #         im_arr = im_arr.astype(np.float64)
        #         im_arr = preprocess_input(im_arr)

        #         # output vgg16 without 3 fc layers
        #         features = self.model.predict(im_arr)
        #         features_ls.append(features)

            image_paths_list = [os.path.join(path, 'frame{}.jpg'.format(frame_count)) for frame_count in range(1, 11, 1)]
            features_ls = self.process_images(image_paths_list)
            all_data[0] = features_ls

        return all_data

    def process_images(self, image_paths_list):
        model = VGG16(weights='imagenet', include_top=False)

        p = mp.Pool(mp.cpu_count())
        images = p.map(Image.open, image_paths_list)
        images = list(images)
        resized_img = p.map(resize_method, images)
        resized_img = np.concatenate(list(resized_img), axis=0)
        features = model.predict(resized_img, batch_size=10)

        p.close()
        p.join()

        return features

    def split_train_test(self):
        data = load_features

    def train(self, X, y, lr = 1e-3):
        num_classes = len(np.unique(y))

        # create new model

        # Temporal max pooling
        x = Input(shape = (10, 7, 7, 512))
        mp = MaxPooling3D(pool_size=(3, 2, 2), strides=(3, 2, 2), padding='valid', data_format='channels_last')(x)
        mp_flat = Flatten()(mp)
        fc1 = Dense(units = 2048, kernel_regularizer=regularizers.l2(self.reg))(mp_flat)
        # fc2 = Dense(units = 512, kernel_regularizer=regularizers.l2(self.reg))(fc1)
        fc3 = Dense(units = num_classes, kernel_regularizer=regularizers.l2(self.reg))(fc1)
        sf = Activation('softmax')(fc3)
        add_model = Model(inputs=x, outputs=sf)
        sgd_m = optimizers.SGD(lr=lr, decay=1e-6, momentum=0.9, nesterov=True)
        add_model.compile(optimizer=sgd_m,
                      loss='categorical_crossentropy',
                      metrics=['accuracy'])

        from keras.utils import to_categorical

        y = to_categorical(y, num_classes=20)


        bsize = X.shape[0] // 10
        bsize = 30

        print('Model is Training...')
        hist = add_model.fit(X, y, epochs=100, batch_size= bsize, validation_split = 0.2, verbose = 0)

        self.add_model = add_model
        return hist

    def predict(self, Xte, yte):
        ypred = self.add_model.predict(Xte)
        ypred = np.argmax(ypred, axis = 1)
        acc = np.mean(ypred == yte)
        print('Video Classification Accuracy: {0}'.format(acc))



def resize_method(im):
    im_resized = im.resize((224, 224))
    im_arr = np.expand_dims(im_resized, axis=0) # add one dimension as 1
    im_arr.flags.writeable = True
    im_arr = im_arr.astype(np.float64)
    im_arr = preprocess_input(im_arr)
    return img_as_float(im_arr)
