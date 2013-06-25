from numba.decorators import jit
from numba import *
import numpy as np
import numpy.core.umath_tests as ut
from numbapro import guvectorize
from numbapro import cuda
from timeit import default_timer as time
from .support import testcase, main

@guvectorize([void(f4[:,:], f4[:,:], f4[:,:])],
             '(m,n),(n,p)->(m,p)',
             target='gpu')
def matmulcore(A, B, C):
    m, n = A.shape
    n, p = B.shape
    for i in range(m):
        for j in range(p):
            C[i, j] = 0
            for k in range(n):
                C[i, j] += A[i, k] * B[k, j]

gufunc = matmulcore
gufunc.max_blocksize = 512

non_stream_speedups = []
stream_speedups = []

@testcase
def test_gufunc():
    matrix_ct = 1001 # an odd number to test thread/block division in CUDA
    A = np.arange(matrix_ct * 2 * 4, dtype=np.float32).reshape(matrix_ct, 2, 4)
    B = np.arange(matrix_ct * 4 * 5, dtype=np.float32).reshape(matrix_ct, 4, 5)

    ts = time()
    C = gufunc(A, B)
    tcuda = time() - ts

    ts = time()
    Gold = ut.matrix_multiply(A, B)
    tcpu = time() - ts

    non_stream_speedups.append(tcpu / tcuda)
    assert np.allclose(C, Gold)


@testcase
def test_gufunc_adjust_blocksize():
    matrix_ct = 1001 # an odd number to test thread/block division in CUDA
    A = np.arange(matrix_ct * 2 * 4, dtype=np.float32).reshape(matrix_ct, 2, 4)
    B = np.arange(matrix_ct * 4 * 5, dtype=np.float32).reshape(matrix_ct, 4, 5)

    ts = time()
    gufunc.max_blocksize = 32
    C = gufunc(A, B)
    tcuda = time() - ts

    ts = time()
    Gold = ut.matrix_multiply(A, B)
    tcpu = time() - ts
    
    assert np.allclose(C, Gold)

@testcase
def test_gufunc_stream():
    matrix_ct = 1001 # an odd number to test thread/block division in CUDA
    A = np.arange(matrix_ct * 2 * 4, dtype=np.float32).reshape(matrix_ct, 2, 4)
    B = np.arange(matrix_ct * 4 * 5, dtype=np.float32).reshape(matrix_ct, 4, 5)

    ts = time()
    stream = cuda.stream()
    dA = cuda.to_device(A, stream)
    dB = cuda.to_device(B, stream)
    dC = gufunc(dA, dB, stream=stream)
    C = dC.copy_to_host(stream=stream)
    stream.synchronize()
    tcuda = time() - ts

    ts = time()
    Gold = ut.matrix_multiply(A, B)
    tcpu = time() - ts

    stream_speedups.append(tcpu / tcuda)
    assert np.allclose(C, Gold)

if __name__ == '__main__':
    main()
