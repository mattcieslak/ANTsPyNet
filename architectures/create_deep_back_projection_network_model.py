
from keras.models import Model
from keras.layers import (Input, Add, Subtract,
                          PReLU, Concatenate,
                          Conv2D, Conv2DTranspose,
                          Conv3D, Conv3DTranspose)

def create_deep_back_projection_network_model_2d(input_image_size,
                                                 number_of_outputs=1,
                                                 number_of_base_filters=64,
                                                 number_of_feature_filters=256,
                                                 number_of_back_projection_stages=7,
                                                 convolution_kernel_size=(12, 12),
                                                 strides=(8, 8),
                                                 last_convolution=(3, 3),
                                                 number_of_loss_functions=1
                                                ):
    """
    2-D implementation of the deep back-projection network.

    Creates a keras model of the deep back-project network for image super
    resolution.  More information is provided at the authors' website:

            https://www.toyota-ti.ac.jp/Lab/Denshi/iim/members/muhammad.haris/projects/DBPN.html

    with the paper available here:

            https://arxiv.org/abs/1803.02735

    This particular implementation was influenced by the following keras (python)
    implementation:

            https://github.com/rajatkb/DBPN-Keras

    with help from the original author's Caffe and Pytorch implementations:

            https://github.com/alterzero/DBPN-caffe
            https://github.com/alterzero/DBPN-Pytorch

    :param input_image_size: Used for specifying the input tensor shape.  The
      shape (or dimension) of that tensor is the image dimensions followed by
      the number of channels (e.g., red, green, and blue).
    :param number_of_outputs: number of outputs (e.g., 3 for RGB images).
    :param number_of_feature_filters: number of feature filters.
    :param number_of_base_filters: number of base filters.
    :param number_of_back_projection_stages: number of up-down-projection stages.
      This number includes the final up block.
    :param convolution_kernel_size: kernel size for certain convolutional layers.
      This strides are dependent on the scale factor discussed in original paper.
      Factors used in the original implementation are as follows:
        2x --> convolutionKernelSize=(6, 6),
        4x --> convolutionKernelSize=(8, 8),
        8x --> convolutionKernelSize=(12, 12).  We default to 8x parameters.
    :param strides: strides for certain convolutional layers.  This and the
      convolution_kernel_size are dependent on the scale factor discussed in
      original paper.  Factors used in the original implementation are as follows:
        2x --> strides = (2, 2),
        4x --> strides = (4, 4),
        8x --> strides = (8, 8). We default to 8x parameters.
    :param last_convolution: the kernel size for the last convolutional layer
    :param number_of_loss_functions: the number of data targets, e.g. 2 for 2 targets
    :returns: a keras model defining the deep back-projection network.
    """

    def up_block_2d(L, number_of_filters=64, kernel_size=(12, 12), strides=(8, 8),
                    include_dense_convolution_layer=False):
        if include_dense_convolution_layer == True:
            L = Conv2D(filters = number_of_filters,
                       use_bias=True,
                       kernel_size=(1, 1),
                       strides=(1, 1),
                       padding='same')(L)
            L = PReLU(alpha_initializer='zero',
                      shared_axes=[1, 2])(L)

        # Scale up
        H0 = Conv2DTranspose(filters=number_of_filters,
                             kernel_size=kernel_size,
                             strides=strides,
                             kernel_initializer='glorot_uniform',
                             padding='same')(L)
        H0 = PReLU(alpha_initializer='zero',
                   shared_axes=[1, 2])(H0)

        # Scale down
        L0 = Conv2D(filters=number_of_filters,
                    kernel_size=kernel_size,
                    strides=strides,
                    kernel_initializer='glorot_uniform',
                    padding='same')(H0)
        L0 = PReLU(alpha_initializer='zero',
                   shared_axes=[1, 2])(L0)

        # Residual
        E = Subtract()([L0, L])

        # Scale residual up
        H1 = Conv2DTranspose(filters=number_of_filters,
                             kernel_size=kernel_size,
                             strides=strides,
                             kernel_initializer='glorot_uniform',
                             padding='same')(E)
        H1 = PReLU(alpha_initializer='zero',
                   shared_axes=[1, 2])(H1)

        # Output feature map
        up_block = Add()([H0, H1])

        return(up_block)


    def down_block_2d(H, number_of_filters=64, kernel_size=(12, 12), strides=(8, 8),
                    include_dense_convolution_layer=False):
        if include_dense_convolution_layer == True:
            H = Conv2D(filters = number_of_filters,
                       use_bias=True,
                       kernel_size=(1, 1),
                       strides=(1, 1),
                       padding='same')(H)
            H = PReLU(alpha_initializer='zero',
                      shared_axes=[1, 2])(H)

        # Scale down
        L0 = Conv2D(filters=number_of_filters,
                    kernel_size=kernel_size,
                    strides=strides,
                    kernel_initializer='glorot_uniform',
                    padding='same')(H)
        L0 = PReLU(alpha_initializer='zero',
                   shared_axes=[1, 2])(L0)

        # Scale up
        H0 = Conv2DTranspose(filters=number_of_filters,
                             kernel_size=kernel_size,
                             strides=strides,
                             kernel_initializer='glorot_uniform',
                             padding='same')(L0)
        H0 = PReLU(alpha_initializer='zero',
                   shared_axes=[1, 2])(H0)

        # Residual
        E = Subtract()([H0, H])

        # Scale residual down
        L1 = Conv2D(filters=number_of_filters,
                    kernel_size=kernel_size,
                    strides=strides,
                    kernel_initializer='glorot_uniform',
                    padding='same')(E)
        L1 = PReLU(alpha_initializer='zero',
                   shared_axes=[1, 2])(L1)

        # Output feature map
        down_block = Add()([L0, L1])

        return(down_block)

    inputs = Input(shape=input_image_size)

    # Initial feature extraction
    model = Conv2D(filters=number_of_feature_filters,
                   kernel_size=(3, 3),
                   strides=(1, 1),
                   padding='same',
                   kernel_initializer='glorot_uniform')(inputs)
    model = PReLU(alpha_initializer='zero',
                  shared_axes=[1, 2])(model)

    # Feature smashing
    model = Conv2D(filters=number_of_base_filters,
                   kernel_size=(1, 1),
                   strides=(1, 1),
                   padding='same',
                   kernel_initializer='glorot_uniform')(model)
    model = PReLU(alpha_initializer='zero',
                  shared_axes=[1, 2])(model)

    # Back projection
    up_projection_blocks = []
    down_projection_blocks = []

    model = up_block_2d(model, number_of_filters=number_of_base_filters,
      kernel_size=convolution_kernel_size, strides=strides)
    up_projection_blocks.append(model)

    for i in range(number_of_back_projection_stages):
        if i == 0:
            model = down_block_2d(model, number_of_filters=number_of_base_filters,
              kernel_size=convolution_kernel_size, strides=strides)
            down_projection_blocks.append(model)

            model = up_block_2d(model, number_of_filters=number_of_base_filters,
              kernel_size=convolution_kernel_size, strides=strides)
            up_projection_blocks.append(model)

            model = Concatenate()(up_projection_blocks)
        else:
            model = down_block_2d(model, number_of_filters=number_of_base_filters,
              kernel_size=convolution_kernel_size, strides=strides,
              include_dense_convolution_layer=True)
            down_projection_blocks.append(model)
            model = Concatenate()(down_projection_blocks)

            model = up_block_2d(model, number_of_filters=number_of_base_filters,
              kernel_size=convolution_kernel_size, strides=strides,
              include_dense_convolution_layer=True)
            up_projection_blocks.append(model)

            model = Concatenate()(up_projection_blocks)

    # Final convolution layer
    outputs = Conv2D(filters=number_of_outputs,
                     kernel_size=last_convolution,
                     strides=(1, 1),
                     padding = 'same',
                     kernel_initializer = "glorot_uniform")(model)

    if number_of_loss_functions == 1:
        deep_back_projection_network_model = Model(inputs=inputs, outputs=outputs)
    else:
        outputList=[]
        for k in range(number_of_loss_functions):
            outputList.append(outputs)
        deep_back_projection_network_model = Model(inputs=inputs, outputs=outputList)

    return(deep_back_projection_network_model)


def create_deep_back_projection_network_model_3d(input_image_size,
                                                 number_of_outputs=1,
                                                 number_of_base_filters=64,
                                                 number_of_feature_filters=256,
                                                 number_of_back_projection_stages=7,
                                                 convolution_kernel_size=(12, 12, 12),
                                                 strides=(8, 8, 8),
                                                 last_convolution=(3, 3, 3),
                                                 number_of_loss_functions=1
                                                ):
    """
    3-D implementation of the deep back-projection network.

    Creates a keras model of the deep back-project network for image super
    resolution.  More information is provided at the authors' website:

            https://www.toyota-ti.ac.jp/Lab/Denshi/iim/members/muhammad.haris/projects/DBPN.html

    with the paper available here:

            https://arxiv.org/abs/1803.02735

    This particular implementation was influenced by the following keras (python)
    implementation:

            https://github.com/rajatkb/DBPN-Keras

    with help from the original author's Caffe and Pytorch implementations:

            https://github.com/alterzero/DBPN-caffe
            https://github.com/alterzero/DBPN-Pytorch

    :param input_image_size: Used for specifying the input tensor shape.  The
      shape (or dimension) of that tensor is the image dimensions followed by
      the number of channels (e.g., red, green, and blue).
    :param number_of_outputs: number of outputs (e.g., 3 for RGB images).
    :param number_of_feature_filters: number of feature filters.
    :param number_of_base_filters: number of base filters.
    :param number_of_back_projection_stages: number of up-down-projection stages.
      This number includes the final up block.
    :param convolution_kernel_size: kernel size for certain convolutional layers.
      This strides are dependent on the scale factor discussed in original paper.
      Factors used in the original implementation are as follows:
        2x --> convolutionKernelSize=(6, 6, 6),
        4x --> convolutionKernelSize=(8, 8, 6),
        8x --> convolutionKernelSize=(12, 12, 12).  We default to 8x parameters.
    :param strides: strides for certain convolutional layers.  This and the
      convolution_kernel_size are dependent on the scale factor discussed in
      original paper.  Factors used in the original implementation are as follows:
        2x --> strides = (2, 2, 2),
        4x --> strides = (4, 4, 4),
        8x --> strides = (8, 8, 8). We default to 8x parameters.
    :param last_convolution: the kernel size for the last convolutional layer
    :param number_of_loss_functions: the number of data targets, e.g. 2 for 2 targets
    :returns: a keras model defining the deep back-projection network.
    """

    def up_block_3d(L, number_of_filters=64, kernel_size=(12, 12, 12), strides=(8, 8, 8),
                    include_dense_convolution_layer=False):
        if include_dense_convolution_layer == True:
            L = Conv2D(filters = number_of_filters,
                       use_bias=True,
                       kernel_size=(1, 1, 1),
                       strides=(1, 1, 1),
                       padding='same')(L)
            L = PReLU(alpha_initializer='zero',
                      shared_axes=[1, 2, 3])(L)

        # Scale up
        H0 = Conv3DTranspose(filters=number_of_filters,
                             kernel_size=kernel_size,
                             strides=strides,
                             kernel_initializer='glorot_uniform',
                             padding='same')(L)
        H0 = PReLU(alpha_initializer='zero',
                   shared_axes=[1, 2, 3])(H0)

        # Scale down
        L0 = Conv3D(filters=number_of_filters,
                    kernel_size=kernel_size,
                    strides=strides,
                    kernel_initializer='glorot_uniform',
                    padding='same')(H0)
        L0 = PReLU(alpha_initializer='zero',
                   shared_axes=[1, 2, 3])(L0)

        # Residual
        E = Subtract()([L0, L])

        # Scale residual up
        H1 = Conv3DTranspose(filters=number_of_filters,
                             kernel_size=kernel_size,
                             strides=strides,
                             kernel_initializer='glorot_uniform',
                             padding='same')(E)
        H1 = PReLU(alpha_initializer='zero',
                   shared_axes=[1, 2, 3])(H1)

        # Output feature map
        up_block = Add()([H0, H1])

        return(up_block)


    def down_block_3d(H, number_of_filters=64, kernel_size=(12, 12, 12), strides=(8, 8, 8),
                    include_dense_convolution_layer=False):
        if include_dense_convolution_layer == True:
            H = Conv3D(filters = number_of_filters,
                       use_bias=True,
                       kernel_size=(1, 1, 1),
                       strides=(1, 1, 1),
                       padding='same')(H)
            H = PReLU(alpha_initializer='zero',
                      shared_axes=[1, 2, 3])(H)

        # Scale down
        L0 = Conv3D(filters=number_of_filters,
                    kernel_size=kernel_size,
                    strides=strides,
                    kernel_initializer='glorot_uniform',
                    padding='same')(H)
        L0 = PReLU(alpha_initializer='zero',
                   shared_axes=[1, 2, 3])(L0)

        # Scale up
        H0 = Conv3DTranspose(filters=number_of_filters,
                             kernel_size=kernel_size,
                             strides=strides,
                             kernel_initializer='glorot_uniform',
                             padding='same')(L0)
        H0 = PReLU(alpha_initializer='zero',
                   shared_axes=[1, 2, 3])(H0)

        # Residual
        E = Subtract()([H0, H])

        # Scale residual down
        L1 = Conv3D(filters=number_of_filters,
                    kernel_size=kernel_size,
                    strides=strides,
                    kernel_initializer='glorot_uniform',
                    padding='same')(E)
        L1 = PReLU(alpha_initializer='zero',
                   shared_axes=[1, 2, 3])(L1)

        # Output feature map
        down_block = Add()([L0, L1])

        return(down_block)

    inputs = Input(shape=input_image_size)

    # Initial feature extraction
    model = Conv3D(filters=number_of_feature_filters,
                   kernel_size=(3, 3, 3),
                   strides=(1, 1, 1),
                   padding='same',
                   kernel_initializer='glorot_uniform')(inputs)
    model = PReLU(alpha_initializer='zero',
                  shared_axes=[1, 2, 3])(model)

    # Feature smashing
    model = Conv3D(filters=number_of_base_filters,
                   kernel_size=(1, 1, 1),
                   strides=(1, 1, 1),
                   padding='same',
                   kernel_initializer='glorot_uniform')(model)
    model = PReLU(alpha_initializer='zero',
                  shared_axes=[1, 2, 3])(model)

    # Back projection
    up_projection_blocks = []
    down_projection_blocks = []

    model = up_block_3d(model, number_of_filters=number_of_base_filters,
      kernel_size=convolution_kernel_size, strides=strides)
    up_projection_blocks.append(model)

    for i in range(number_of_back_projection_stages):
        if i == 0:
            model = down_block_3d(model, number_of_filters=number_of_base_filters,
              kernel_size=convolution_kernel_size, strides=strides)
            down_projection_blocks.append(model)

            model = up_block_3d(model, number_of_filters=number_of_base_filters,
              kernel_size=convolution_kernel_size, strides=strides)
            up_projection_blocks.append(model)

            model = Concatenate()(up_projection_blocks)
        else:
            model = down_block_3d(model, number_of_filters=number_of_base_filters,
              kernel_size=convolution_kernel_size, strides=strides,
              include_dense_convolution_layer=True)
            down_projection_blocks.append(model)
            model = Concatenate()(down_projection_blocks)

            model = up_block_3d(model, number_of_filters=number_of_base_filters,
              kernel_size=convolution_kernel_size, strides=strides,
              include_dense_convolution_layer=True)
            up_projection_blocks.append(model)

            model = Concatenate()(up_projection_blocks)

    # Final convolution layer
    outputs = Conv3D(filters=number_of_outputs,
                     kernel_size=last_convolution,
                     strides=(1, 1, 1),
                     padding = 'same',
                     kernel_initializer = "glorot_uniform")(model)

    if number_of_loss_functions == 1:
        deep_back_projection_network_model = Model(inputs=inputs, outputs=outputs)
    else:
        outputList=[]
        for k in range(number_of_loss_functions):
            outputList.append(outputs)
        deep_back_projection_network_model = Model(inputs=inputs, outputs=outputList)

    return(deep_back_projection_network_model)


























