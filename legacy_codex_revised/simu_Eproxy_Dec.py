#!/usr/bin/python
# -*- coding:utf-8 -*- 
import astropy.io.fits as pf
from numpy import *
from scipy import integrate
from scipy import interpolate as intp
import matplotlib.pyplot as plt 
#import os,datetime
import use
from use1 import *
# set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=3, floatmode='maxprec')
#start_time = datetime.datetime.now() 
#print( datetime.datetime.now() - start_time )

'############################  #############################'
'########################### !! ############################'
d2r = 180./pi


coszs = linspace(-1, 1, 200+1)
lgEprs  = log10( use.ebs(1e1, 1e8, 7*30) )
pdf2D = loadtxt('data_output/bkgd_pdf_2D_86b.txt')*2*pi  # *2*pi is becuase the _bkgd_spatial_pdf was normalized to 1/2/pi

# Check if normalized
tmp = integrate.simps( pdf2D, lgEprs, axis=1 ) 
print('# Check if normalized', integrate.simps(tmp, coszs) )

pdf2D_intp = intp.interp2d( lgEprs, coszs, pdf2D, bounds_error=True ) 

def generate_rand_2D(pdf2D_, x_min, x_max, y_min, y_max, Z_max, N_simu_):
    #'This is for the case of using an analytic PDF; Even if it is not analytic, we can interpolate. So it is universal for 1D random number generation.'
    #'Later make it a universal function'
    #'Later change the names of the variables below'
    #'Later make it more self-adaptive so that it gives me the number of simulated events I want'
    #'Checked'
    rand_x = random.uniform( x_min, x_max, size=N_simu_ )
    rand_y = random.uniform( y_min, y_max, size=N_simu_ )

    rand_z = zeros(N_simu_)
    for ii in range(N_simu_): # This may be slow; later can improve the speed from here.
        rand_z[ii] = pdf2D_(rand_x[ii], rand_y[ii]) 
        # pdf2D_(rand_x, rand_y)  This gives a 2D array...... not what i want.

    rand_Z = random.uniform(0, Z_max, size=N_simu_)

    if len(where( rand_z > Z_max )[0])>0:
        print('# Error, rand_z > Z_max')
        exit()
    idx = where( rand_Z < rand_z )[0]

    return rand_x[idx], rand_y[idx]

#pdf2d_max = pdf2D.max()
pdf2d_max = pdf2D.max()
lgEprs_simu, coszs_simu = generate_rand_2D(pdf2D_intp, lgEprs.min(), lgEprs.max(), coszs.min(), coszs.max(), pdf2d_max*1.1, int(1e6))







#backup
