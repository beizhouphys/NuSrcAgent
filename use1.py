#!/usr/bin/python
import numpy as np



def ppp(arr):
    'print array'
    if np.isscalar(arr):
        print( arr )
        return
    print(arr)
    print(arr.shape)

def pppp(arr):
    'print array'
    if np.isscalar(arr):
        print( arr )
        return
    print(arr.shape)

def pcm(num): # 'print numbers with comma'
    print(f'{num:,}')


def printt(expression):
    result = eval(expression)
    
    print(expression)
    print(result)



#backup
