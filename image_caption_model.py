# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import cv2
import keras
import re
import nltk
from nltk.corpus import stopwords
import string
import json
from time import time
import pickle
from keras.applications.vgg16 import VGG16
from keras.applications.resnet50 import ResNet50, preprocess_input, decode_predictions
from keras.preprocessing import image
from keras.models import Model, load_model
from keras.preprocessing.sequence import pad_sequences
from keras.utils import to_categorical
from keras.layers import Input, Dense, Dropout, Embedding, LSTM
from keras.layers.merge import add



!wget https://github.com/jbrownlee/Datasets/releases/download/Flickr8k/Flickr8k_Dataset.zip

!wget https://github.com/jbrownlee/Datasets/releases/download/Flickr8k/Flickr8k_text.zip

!unzip Flickr8k_Dataset.zip -d all_images

!unzip Flickr8k_text.zip -d all_captions




image_dir = '/content/all_images/Flicker8k_Dataset'
caption_file = '/content/all_captions/Flickr8k.token.txt'
captions = open(caption_file, 'r').read().strip().split('\n')

print(len(captions))

first,second  = captions[0].split('\t')
print(first.split(".")[0])
print(second)

descriptions = {}

for x in captions:
    first,second = x.split('\t')
    img_name = first.split(".")[0]
    
    #if the image id is already present or not
    if descriptions.get(img_name) is None:
        descriptions[img_name] = []
    
    descriptions[img_name].append(second)

descriptions["979383193_0a542a059d"]

img = cv2.imread(image_dir+"/"+"979383193_0a542a059d.jpg")
img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
plt.imshow(img)
plt.axis("off")
plt.show()

def clean_text(st):
    st = st.lower()
    st = re.sub("[^a-z]+"," ",st)
    st = st.split()
    
    st  = [s for s in st if len(s)>1]
    st = " ".join(st)
    return st

clean_text("The dogs 8 are * shouting at night # 09")

for key,caption_list in descriptions.items():
    for i in range(len(caption_list)):
        caption_list[i] = clean_text(caption_list[i])

descriptions["1000268201_693b08cb0e"]

train_file_data = '/content/all_captions/Flickr_8k.trainImages.txt'

train_file = open(train_file_data, 'r').read()
train = [row.split(".")[0] for row in train_file.split("\n")[:-1]]

print(train[:5])

test_file_data = '/content/all_captions/Flickr_8k.testImages.txt'

test_file = open(test_file_data,'r').read()
test = [row.split(".")[0] for row in test_file.split("\n")[:-1]]

print(test[:5])

train_descriptions = {}

for img_id in train:
    train_descriptions[img_id] = []
    for cap in descriptions[img_id]:
        cap_to_append = "startseq "  + cap + " endseq"
        train_descriptions[img_id].append(cap_to_append)

train_descriptions["2903617548_d3e38d7f88"]

model = ResNet50(weights="imagenet",input_shape=(224,224,3))
model.summary()

model_new = Model(model.input,model.layers[-2].output)

def preprocess_img(img):
    img = image.load_img(img,target_size=(224,224))
    img = image.img_to_array(img)
    img = np.expand_dims(img,axis=0)
    # Normalisation
    img = preprocess_input(img)
    return img

img = preprocess_img(image_dir+"1000268201_693b08cb0e.jpg")
plt.imshow(img[0])
plt.axis("off")
plt.show()

def encode_image(img):
    img = preprocess_img(img)
    feature_vector = model_new.predict(img)
    
    feature_vector = feature_vector.reshape((-1,))
    #print(feature_vector.shape)
    return feature_vector

encode_image(image_dir+"1000268201_693b08cb0e.jpg")

start = time()
encoding_train = {}
#image_id -->feature_vector extracted from Resnet Image

for ix,img_id in enumerate(train):
    img_path = image_dir+"/"+img_id+".jpg"
    encoding_train[img_id] = encode_image(img_path)
    
    if ix%100==0:
        print("Encoding in Progress Time step %d "%ix)
        
end_t = time()
print("Total Time Taken :",end_t-start)

print(img_path)

!mkdir saved1

with open("saved1/encoded_train_features.pkl","wb") as f:
    pickle.dump(encoding_train,f)

start = time()
encoding_test = {}
#image_id -->feature_vector extracted from Resnet Image

for ix,img_id in enumerate(test):
    img_path = image_dir+"/"+img_id+".jpg"
    encoding_test[img_id] = encode_image(img_path)
    
    if ix%100==0:
        print("Test Encoding in Progress Time step %d "%ix)
        
end_t = time()
print("Total Time Taken(test) :",end_t-start)

with open("saved1/encoded_test_features.pkl","wb") as f:
    pickle.dump(encoding_test,f)

"""Vocabulary"""

with open("descriptions_1.txt","w") as f:
    f.write(str(descriptions))

descriptions = None
with open("descriptions_1.txt",'r') as f:
    descriptions= f.read()
    f.close()

json_acceptable_string = descriptions.replace("'","\"")

descriptions = json.loads(json_acceptable_string)

print(type(descriptions))

all_vocab = []

for key in descriptions.keys():
  [all_vocab.append(i) for des in descriptions[key] for i in des.split()]

print("Vocabulary size: %d"%len(all_vocab))
print(all_vocab[:15])

import collections

counter = collections.Counter(all_vocab)
dic = dict(counter)

threshold_value = 10
sorted_dic = sorted(dic.items(),reverse=True,key=lambda x:x[1])
sorted_dic =  [x for x in sorted_dic if x[1]>threshold_value]

all_vocab = [x[0] for x in sorted_dic]
print(len(all_vocab))

#Data preprocessing for Captions

word_to_idx = {}
idx_to_word = {}

for i,word in enumerate(all_vocab):
    word_to_idx[word] = i+1
    idx_to_word[i+1] = word

word_to_idx["dog"]
print(word_to_idx)
idx_to_word[1]
print(idx_to_word)
print(len(idx_to_word))

idx_to_word[1846] = 'startseq'
word_to_idx['startseq'] = 1846

idx_to_word[1847] = 'endseq'
word_to_idx['endseq'] = 1847

vocab_size = len(word_to_idx) + 1
print("Vocab Size",vocab_size)

max_len = 0 
for key in train_descriptions.keys():
    for cap in train_descriptions[key]:
        max_len = max(max_len,len(cap.split()))
        
print(max_len)

!mkdir storage

with open("storage/word_to_idx.pkl","wb") as w2i:
    pickle.dump(word_to_idx,w2i)

with open("storage/idx_to_word.pkl","wb") as i2w:
    pickle.dump(idx_to_word,i2w)

def data_generator(train_descriptions,encoding_train,word_to_idx,max_len,batch_size):
  
    X1,X2, y = [],[],[]
    
    n =0
    while True:
        for key,desc_list in train_descriptions.items():
            n += 1
            
            photo = encoding_train[key+".jpg"]
            
            for desc in desc_list:
                
                seq = [word_to_idx[word] for word in desc.split() if word in word_to_idx]
                for i in range(1,len(seq)):
                    xi = seq[0:i]
                    yi = seq[i]
                    
                    #0 denote padding word
                    xi = pad_sequences([xi],maxlen=max_len,value=0,padding='post')[0]
                    yi = to_categorcial([yi],num_classes=vocab_size)[0]
                    
                    X1.append(photo)
                    X2.append(xi)
                    y.append(yi)
                    
                if n==batch_size:
                    yield [[np.array(X1),np.array(X2)],np.array(y)]
                    X1,X2,y = [],[],[]
                    n = 0

#word_embedding

!wget http://nlp.stanford.edu/data/glove.6B.zip

!unzip glove.6B.zip

f = open("/content/glove.6B.50d.txt",encoding='utf8')

embedding_index = {}

for line in f:
    values = line.split()
    
    word = values[0]
    word_embedding = np.array(values[1:],dtype='float')
    embedding_index[word] = word_embedding

f.close()

embedding_index['apple']

def get_embedding_matrix():
    emb_dim = 50
    matrix = np.zeros((vocab_size,emb_dim))
    for word,idx in word_to_idx.items():
        embedding_vector = embedding_index.get(word)
        
        if embedding_vector is not None:
            matrix[idx] = embedding_vector
            
    return matrix

embedding_matrix = get_embedding_matrix()
embedding_matrix.shape

#model architecture
input_img_features = Input(shape=(2048,))
inp_img1 = Dropout(0.3)(input_img_features)
inp_img2 = Dense(256,activation='relu')(inp_img1)

# Captions as Input
input_captions = Input(shape=(max_len,))
inp_cap1 = Embedding(input_dim=vocab_size,output_dim=50,mask_zero=True)(input_captions)
inp_cap2 = Dropout(0.3)(inp_cap1)
inp_cap3 = LSTM(256)(inp_cap2)

decoder1 = add([inp_img2,inp_cap3])
decoder2 = Dense(256,activation='relu')(decoder1)
outputs = Dense(vocab_size,activation='softmax')(decoder2)
# Combined Model
model = Model(inputs=[input_img_features,input_captions],outputs=outputs)

model.summary()

#Important Thing - Embedding Layer
model.layers[2].set_weights([embedding_matrix])
model.layers[2].trainable = False

model.compile(loss='categorical_crossentropy',optimizer="adam")


epochs = 20
batch_size = 3

steps = len(train_descriptions)//batch_size

for i in range(epochs):
    generator = data_generator(train_descriptions,encoding_train,word_to_idx,max_len,batch_size)
    model.fit_generator(generator,epochs=1,steps_per_epoch=steps,verbose=1)
    model.save('content/saved/model_'+str(i)+'.h5')
    
model = load_model('content/saved/model_15.h5')


def predict_caption(photo):
    
    in_text = "startseq"
    for i in range(max_len):
        sequence = [word_to_idx[w] for w in in_text.split() if w in word_to_idx]
        sequence = pad_sequences([sequence],maxlen=max_len,padding='post')
        
        ypred = model.predict([photo,sequence])
        ypred = ypred.argmax() #WOrd with max prob always - Greedy Sampling
        word = idx_to_word[ypred]
        in_text += (' ' + word)
        
        if word == "endseq":
            break
    
    final_caption = in_text.split()[1:-1]
    final_caption = ' '.join(final_caption)
    return final_caption
