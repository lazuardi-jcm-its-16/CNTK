import sys
import os
import cntk.device as device
#device.set_default_device(device.cpu())
import numpy as np
import ReasoNet.asr as asr
from cntk.blocks import Placeholder, Constant,initial_state_default_or_None, _is_given, _get_current_default_options
from cntk.ops import input_variable, past_value, future_value
from cntk.io import MinibatchSource
from cntk import Trainer, Axis, device, combine
from cntk.layers import Recurrence, Convolution
from cntk.utils import _as_tuple
import cntk.ops as ops
import cntk
import cntk.initializer as initializer
import ReasoNet.wordvocab as vocab
import ReasoNet.utils as utils
import math
import cntk.cntk_py as cntk_py
##########
# Note. for CNN data set, the best results is with settings
# Golve_Embedding, glorot_uniform init, No dropout
# Learning rate: 0.0005
# SoftMax with minus max normed
##########
def testASRTrain(data, epoch_size, max_epochs=1, vocab_dim=101000, entity_dim=101, hidden_dim=300, embedding_dim=100, max_rl_iter =5, embedding_path=None, vocab_path=None, eval_path=None, eval_size=None, model_name='asr'):
  full_name = os.path.basename(data) + '_' + model_name
  train_data = asr.create_reader(data, vocab_dim, entity_dim, True, rand_size=epoch_size)
  eval_data = asr.create_reader(eval_path, vocab_dim, entity_dim, False, rand_size=eval_size) if eval_path is not None else None
  embedding_init = None
  if embedding_path:
    scale = math.sqrt(6/(vocab_dim+embedding_dim))*2
    init = utils.uniform_initializer(scale, -scale/2)
    embedding_init = vocab.load_embedding(embedding_path, vocab_path, embedding_dim, init)
  #model = asr.create_model(vocab_dim, entity_dim, hidden_dim, embedding_init=None, embedding_dim=embedding_dim, model_name = full_name, init=initializer.glorot_uniform())
  model = asr.create_model(vocab_dim, entity_dim, hidden_dim, embedding_init=embedding_init, embedding_dim=embedding_dim, init=initializer.glorot_uniform(), dropout_rate=0.2, model_name = full_name)
  #model = asr.create_model(vocab_dim, entity_dim, hidden_dim, embedding_init=embedding_init, embedding_dim=embedding_dim, init=initializer.glorot_uniform(), dropout_rate=None, model_name = full_name)
  #model = asr.create_model(vocab_dim, entity_dim, hidden_dim, embedding_init=embedding_init, embedding_dim=embedding_dim, init=initializer.glorot_uniform(), dropout_rate=None, model_name = full_name)
  asr.train(model, train_data, max_epochs=max_epochs, epoch_size=epoch_size, save_model_flag=True, model_name=full_name, eval_data=eval_data, eval_size=eval_size)

def testASREval(model_path, eval_path, eval_size, vocab_dim, entity_dim, hidden_dim, embedding_dim):
  print("Evaluate model: {} using data {}".format(model_path, eval_path))
  model = asr.create_model(vocab_dim, entity_dim, hidden_dim, embedding_init=None, embedding_dim=embedding_dim)
  model.restore_model(model_path)
  lf = asr.loss(model)
  eval_data = asr.create_reader(eval_path, vocab_dim, entity_dim, False, rand_size=eval_size)
  mini_batch_size = 30000
  bind = asr.bind_data(lf, eval_data)
  for key in bind.keys():
    if key.name == 'labels':
      label_arg = key
      break
  loss_sum = 0
  acc_sum = 0
  samples_sum = 0
  i = 0
  freq = 5
  m = 0
  batch_id = 0
  while i<eval_size:
    mb = eval_data.next_minibatch(mini_batch_size, bind)
    outs = lf.eval(mb)
    loss = np.sum(outs[lf.outputs[0]])
    acc = np.sum(outs[lf.outputs[-1]])
    i += mb[label_arg].num_samples
    samples = mb[label_arg].num_sequences
    samples_sum += samples
    acc_sum += acc
    loss_sum += loss
    sys.stdout.write('.')
    sys.stdout.flush()
    m+=1
    print("{}:{}: acc: {}, avg: {}".format(m,samples_sum, acc/samples, acc_sum/samples_sum))
  print("")
  print("Evaluation acc: {0}, loss: {1}, samples: {2}".format(acc_sum/samples_sum, loss_sum/samples_sum, samples_sum))

#testReasoNetTrain("data/Williams/train.40000.700.idx", 157183685, max_epochs=10, vocab_dim=40100, entity_dim=101,hidden_dim=384, max_rl_iter=5, embedding_path='data/Glove_Embedding/glove.6B.100d.txt', vocab_path='data/Williams/vocab.40000.idx',eval_path="data/Williams/eval.40000.700.idx", eval_size=460122, model_name='v40k.700.eval.rsn_drop_softnorm_term_softmax_max_rl_5.90.adam')

testASRTrain("data/vocab.101000/train.full.idx", 315926117, max_epochs=2, vocab_dim=101100, entity_dim=101, hidden_dim=384, max_rl_iter=1, embedding_path='data/Glove_Embedding/glove.6B.100d.txt', vocab_path='data/vocab.101000/vocab.101000.idx',eval_path="data/vocab.101000/eval.880.idx", eval_size=541338, model_name='v101k.full.asr.step_1')
# Avg length of cnn: 762
#testASRTrain("data/cnn/questions/train.101k.idx", 289716292, max_epochs=10, vocab_dim=101585, entity_dim=586, hidden_dim=384, max_rl_iter=1, embedding_path='data/Glove_Embedding/glove.6B.100d.txt', vocab_path='data/cnn/questions/vocab.101k.idx',eval_path="data/cnn/questions/validation.101k.idx", eval_size=2291183, model_name='v101k.cnn.all_softmax.RandomEntity.new_adam')
#testASRTrain("data/cnn/questions/train.101k.shuffle.idx", 289716292, 
#  max_epochs=10, vocab_dim=102001, entity_dim=1002, hidden_dim=384, max_rl_iter=1, 
#  embedding_path='data/Glove_Embedding/glove.6B.100d.txt', 
#  vocab_path='data/cnn/questions/vocab.101k.shuffle.idx',
#  eval_path="data/cnn/questions/validation.101k.shuffle.idx", 
#  eval_size=2993016, 
#  model_name='v101k.shuffle.cnn.adam.asr')
#testASRTrain("data/Williams/train.40000.idx", 315926117, max_epochs=3, vocab_dim=40100, entity_dim=101, hidden_dim=384, max_rl_iter=1, embedding_path='data/Glove_Embedding/glove.6B.100d.txt', vocab_path='data/Williams/vocab.40000.idx',eval_path="data/Williams/eval.40000.idx", eval_size=541338, model_name='v40k.ASR.dropout.0.2')

#testASREval("model/model_train.101k.idx_v101k.cnn.all_softmax.RandomEntity.new_adam_040.dnn", eval_path="data/cnn/questions/test.101k.idx", eval_size=2291183, vocab_dim=101585, entity_dim=586, hidden_dim=384, embedding_dim=100)
testASREval("model/model_train.full.idx_v101k.full.asr.step_1_020.dnn", eval_path="data/vocab.101000/eval.297.idx", eval_size=127989, vocab_dim=101100, entity_dim=101, hidden_dim=384, embedding_dim=100)

