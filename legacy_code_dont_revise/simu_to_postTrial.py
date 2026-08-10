#!/usr/bin/python
# -*- coding:utf-8 -*- 
import astropy.io.fits as pf
from numpy import *
#from scipy import integrate
#from scipy import interpolate as intp
import matplotlib.pyplot as plt 
import os,datetime
import use
from scipy.stats import norm
from scipy.stats import chi2
# set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=3, floatmode='maxprec')
#start_time = datetime.datetime.now() 
#print datetime.datetime.now() - start_time

# Read the simu results. Later migth merge with other code

#####################################  ######################################
#################################### !! #####################################
d2r = 180./pi
# 不要老保存...




########################## sig; p-val; trial factor ############################
# '''
dof = 1. #!
N_src = 7

for i in range(1): # Input TS/Sig
    #sig_loc = sqrt(16.626530884299427) #!
    #sig_loc = sqrt(4.1**2) 
    #TS = 3.698812478687614 #!
    #TS = 3.266858558403328
    #TS = 4.145521916798316
    TS = 1.7036144654266536

    # Use chi2 distributioin
    p_loc   = chi2.sf(TS, dof)/2 # /2 bcuz degeneracy of a TS correspond to ns, one positive, the other negative.
    sig_loc  = norm.isf( p_loc,    loc=0, scale=1)

    # Use normal distribution, works only for 1 dof.
    p_loc1   = norm.sf ( sqrt(TS), loc=0, scale=1)
    sig_loc1 = norm.isf( p_loc1,   loc=0, scale=1)

    print(p_loc, sig_loc, p_loc1, sig_loc1)
    #exit()

for i in range(0): # Input p-value
    p_loc = 6e-7  #2.1e-5 #!
    sig_loc = norm.isf( p_loc, loc=0, scale=1)
    print(p_loc, sig_loc )
    exit()
#print(p_loc, sig_loc )
p_glb = 1. - (1.-p_loc)**N_src #! **N, where N is number of trials.
sig_glb = norm.isf( p_glb, loc=0, scale=1) # Must be norm dist here
print( p_glb, sig_glb ) 

exit()
######################### !sig; p-val; trial factor! ###########################
# '''


##################### Loc sig to glb sig from simu data #######################
tmp = loadtxt('data_output_new_data/simu_single_src_analysis.dat').T
tmp[2][where(tmp[3]<0)] *= -1
#TSs = tmp[2][0:17880]
TSs = tmp[2][0:]
N_simu = len(TSs)
print( N_simu )

print( sort(TSs)[::-1] )
#exit()

def p_post(TS_pre):
    Num_lt_TS_pre = len( where(TSs>TS_pre)[0] )
    p_pre = 1. - norm.cdf( sqrt(TS_pre) )
    p_post = float( Num_lt_TS_pre ) / float(N_simu); 
    TS_post =  norm.isf( p_post, loc=0, scale=1)**2 
    return sqrt(TS_pre), p_pre, p_post, sqrt(TS_post), Num_lt_TS_pre, 1./sqrt(Num_lt_TS_pre)


rslt = loadtxt('data_output_new_data/RQs3386_10yrNu_TS_dist_GM2.5_sorted.dat',dtype=str).T
TSs_rslt = array( rslt[2], dtype = float )
#print( TSs_rslt )
print()
for i in range( len(TSs_rslt) ):
    print( p_post(TSs_rslt[i]) )
    if TSs_rslt[i] < 10.:
        break
exit()
#################### !Loc sig to glb sig from simu data! ######################


#backup
