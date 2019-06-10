# coding: utf-8
import numpy as np
from sklearn.model_selection import train_test_split
from keras.models import Sequential, Model
from keras.layers import Dense, Dropout, Flatten, Input, Activation
from keras.layers import Conv2D, MaxPooling2D
from keras.layers.normalization import BatchNormalization
from keras.layers import LeakyReLU, PReLU, Input
from keras.callbacks import EarlyStopping, TensorBoard
import keras.backend.tensorflow_backend as KTF
import tensorflow as tf

import matplotlib.pyplot as plt
import os
from read_training_data_viscos import read_csv_type3
from other_tools.dataset_reduction import data_reduction
from other_tools.complex_layer import MLPLayer
from math import floor

def load_data(path, size):
    fname = path + "train_" + str(size).zfill(3) + "_" + str(size).zfill(3) + ".npz"
    with np.load(fname, allow_pickle = True) as f:
        x_train_img, x_train_param, y_train = f["arr_0"], f["arr_1"], f["arr_2"]
    
    return x_train_img, x_train_param, y_train

def main():
    source = "G:\\Toyota\\Data\\Compressible_Invicid\\training_data\\"
    npz_path = source + "NACA4\\"
    size = 512
    x_train_img, x_train_param, y_train = load_data(path=npz_path, size=size)
    
    x_train_img, x_valid_img, x_train_param, x_valid_param, y_train, y_valid = train_test_split(x_train_img, x_train_param, y_train, test_size = 0.175)

    inputs = Input(shape = (512, 512, 1))
    x = Conv2D(32, kernel_size = (3, 3), input_shape = (512, 512, 1))(inputs)
    x = Activation("relu")(x)
    x = Conv2D(64, (3, 3))(x)
    x = Activation("relu")(x)
    x = MaxPooling2D(pool_size = (2, 2))(x)
    x = Dropout(0.25)(x)
    x = Flatten()(x)
    x = Dense(128)(x)
    x = Activation("relu")(x)
    x = Dropout(0.5)(x)
    x = Dense(10)(x)
    outputs = Activation("linear")(x)
    

if __name__ == '__main__':
    main()
    