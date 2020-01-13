import math
import numpy as np

import paddle
from paddle import fluid
import paddle.fluid.dygraph as dg


class Conv1D(dg.Layer):
    """
    A convolution 1D block implemented with Conv2D. Form simplicity and 
    ensuring the output has the same length as the input, it does not allow 
    stride > 1.
    """

    def __init__(self,
                 in_channels,
                 num_filters,
                 filter_size=3,
                 padding=0,
                 dilation=1,
                 stride=1,
                 groups=None,
                 param_attr=None,
                 bias_attr=None,
                 use_cudnn=True,
                 act=None,
                 data_format='NCT',
                 dtype="float32"):
        super(Conv1D, self).__init__(dtype=dtype)

        self.padding = padding
        self.in_channels = in_channels
        self.num_filters = num_filters
        self.filter_size = filter_size
        self.stride = stride
        self.dilation = dilation
        self.padding = padding
        self.act = act
        self.data_format = data_format

        self.conv = dg.Conv2D(
            in_channels=in_channels,
            num_filters=num_filters,
            filter_size=(1, filter_size),
            stride=(1, stride),
            dilation=(1, dilation),
            padding=(0, padding),
            groups=groups,
            param_attr=param_attr,
            bias_attr=bias_attr,
            use_cudnn=use_cudnn,
            act=act,
            dtype=dtype)

    def forward(self, x):
        """
        Args:
            x (Variable): Shape(B, C_in, 1, T), the input, where C_in means
                input channels.
        Returns:
            x (Variable): Shape(B, C_out, 1, T), the outputs, where C_out means
                output channels (num_filters).
        """
        if self.data_format == 'NTC':
            x = fluid.layers.transpose(x, [0, 2, 1])
        x = fluid.layers.unsqueeze(x, [2])
        x = self.conv(x)
        x = fluid.layers.squeeze(x, [2])
        if self.data_format == 'NTC':
            x = fluid.layers.transpose(x, [0, 2, 1])
        return x

class Pool1D(dg.Layer):
    """
    A Pool 1D block implemented with Pool2D.
    """
    def __init__(self,
                 pool_size=-1, 
                 pool_type='max', 
                 pool_stride=1, 
                 pool_padding=0, 
                 global_pooling=False, 
                 use_cudnn=True, 
                 ceil_mode=False, 
                 exclusive=True,
                 data_format='NCT', 
                 dtype='float32'):
        super(Pool1D, self).__init__(dtype=dtype)
        self.pool_size = pool_size
        self.pool_type = pool_type
        self.pool_stride = pool_stride
        self.pool_padding = pool_padding
        self.global_pooling = global_pooling
        self.use_cudnn = use_cudnn
        self.ceil_mode = ceil_mode
        self.exclusive = exclusive
        self.data_format = data_format
        self.dtype = dtype


        self.pool2d = dg.Pool2D([1,pool_size], pool_type = pool_type,
                                pool_stride = [1,pool_stride], pool_padding = [0, pool_padding],
                                global_pooling = global_pooling, use_cudnn = use_cudnn,
                                ceil_mode = ceil_mode, exclusive = exclusive, dtype = dtype)

    
    def forward(self, x):
        """
        Args:
            x (Variable): Shape(B, C_in, 1, T), the input, where C_in means
                input channels.
        Returns:
            x (Variable): Shape(B, C_out, 1, T), the outputs, where C_out means
                output channels (num_filters).
        """
        if self.data_format == 'NTC':
            x = fluid.layers.transpose(x, [0, 2, 1])
        x = fluid.layers.unsqueeze(x, [2])
        x = self.pool2d(x)
        x = fluid.layers.squeeze(x, [2])
        if self.data_format == 'NTC':
            x = fluid.layers.transpose(x, [0, 2, 1])
        return x

class DynamicGRU(dg.Layer):
    def __init__(self,
                 size,
                 param_attr=None,
                 bias_attr=None,
                 is_reverse=False,
                 gate_activation='sigmoid',
                 candidate_activation='tanh',
                 h_0=None,
                 origin_mode=False,
                 init_size=None):
        super(DynamicGRU, self).__init__()
        self.gru_unit = dg.GRUUnit(
            size * 3,
            param_attr=param_attr,
            bias_attr=bias_attr,
            activation=candidate_activation,
            gate_activation=gate_activation,
            origin_mode=origin_mode)
        self.size = size
        self.h_0 = h_0
        self.is_reverse = is_reverse

    def forward(self, inputs):
        hidden = self.h_0
        res = []
        for i in range(inputs.shape[1]):
            if self.is_reverse:
                i = inputs.shape[1] - 1 - i
            input_ = inputs[:, i:i + 1, :]
            input_ = fluid.layers.reshape(
                input_, [-1, input_.shape[2]], inplace=False)
            hidden, reset, gate = self.gru_unit(input_, hidden)
            hidden_ = fluid.layers.reshape(
                hidden, [-1, 1, hidden.shape[1]], inplace=False)
            res.append(hidden_)
        if self.is_reverse:
            res = res[::-1]
        res = fluid.layers.concat(res, axis=1)
        return res
