#!/usr/bin/python
# -*- coding:utf-8 -*- 
from numpy import *
#from scipy import integrate
#from scipy import interpolate as intp
#import matplotlib.pyplot as plt 
#import os,datetime
#import use
# set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=3, floatmode='maxprec')
#start_time = datetime.datetime.now() 
#print datetime.datetime.now() - start_time

#####################################  ######################################
#################################### !! #####################################
# 不要老保存...


def binomial_test(k, Nsrc):
    p_k = p[k-1]
    from scipy.special import comb
    'Can actually use scipy.stats.binom, but let me do this first.'
    'sometimes comb(Nsrc, ii) is too large and gives nan;  Maybe use 1 - XX so for small k no need to cycle to big numbers, or maybe try scipy.stats.binom'
    rslt = 0
    for ii in range(Nsrc):
        if ii < k:
            continue
        tmp = comb(Nsrc, ii) * p_k**ii * (1.-p_k)**(Nsrc-ii)
        #tmp = numpy.random.binomial()
        rslt += tmp
        if tmp < 1e-100:
            return rslt
    return rslt


#tmp1 = loadtxt('data_output_new_data/RQs3386_10yrNu_TS_dist_GM2.5_sorted.dat',dtype=str).T  ##!!
#tmp1 = loadtxt('./data_output_new_data/RFC2020d_10yrNu_TS_dist_GM2.5_sorted.dat',dtype=str).T 
tmp1 = loadtxt('data_output/sources_try/20231024_2305.17030_table1_LHAASO_1st_catalog_TS_dist_GM2.53_sorted.txt',dtype=str).T 
Nsrc = tmp1.shape[1] 
p  = array(tmp1[4], dtype=float)
ns = array(tmp1[3], dtype=float)

for ii in range(0):
    # Reproduced the results of 1910.08488 ppr # not
    p = [1.8e-5, 1.905e-4, 1.5849e-3, 1.820e-3, 10**-1.42, 10**-1.32, 10**-1.09, 10**-1.09, 10**-1.02, ] 
    Nsrc=97 

from scipy.stats import norm
print('# Number, p_glb, sig_glb')
for ik in array(range(Nsrc))+1:
    if ns[ik-1]<0:
        print('# \hat{n}_s < 0, stop')
        break
    p_glb = binomial_test(ik, Nsrc)
    sig_glb = norm.isf( p_glb, loc=0, scale=1)
    print( ik, p_glb, sig_glb )



#backup
