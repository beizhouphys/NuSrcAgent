#!/usr/bin/python
import astropy.io.fits as pf
from numpy import *
import matplotlib.pyplot as plt 
import use
from use1 import *
from scipy.stats import chi2

#from scipy import integrate
#from scipy import interpolate as intp
#import os,datetime
import healpy as hp

# set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=3, floatmode='maxprec')
#start_time = datetime.datetime.now() 
#print( datetime.datetime.now() - start_time )

'############################  #############################'
'########################### !! ############################'
d2r = 180./pi


tmp = loadtxt('data_output/sources_try/20220629_Sara_healpix512_10yrNu_TS_dist_GM2.53.txt').T
#savetxt('ttt_combined_TS_ns.txt', array([tmp[2],tmp[3]]).T)

#tmp = loadtxt('ttt_combined_TS_ns.txt').T
idx = tmp[0]
RAs = tmp[1]/d2r; Decs = tmp[2]/d2r
nss = tmp[3]; TSs = tmp[4]; 


# Use chi2 distributioin
dof = 1. #!
ps_loc   = chi2.sf(TSs, dof)/2 # /2 bcuz degeneracy of a TS correspond to ns, one positive, the other negative.
#sig_loc  = norm.isf( p_loc,    loc=0, scale=1)

ps_loc[ where(nss<0) ] = 1
ps_loc[ where(abs(Decs)>87/d2r) ] = 1


#print(ps_loc)
savetxt('ttt_combined_save.txt', array([idx, RAs*d2r, Decs*d2r, nss, TSs, ps_loc]).T, fmt='%f')


'Events to healpix map'
'thetas_ in rad, co latitude;  phis_ in rad, longitude.'
Nside = 512
Npix = 12*Nside**2

indices = arange(Npix) # This gives all the indices, [0,1,2,3,...]
m = zeros(Npix)
m[indices] = ps_loc
hp.mollview(m)

hp.fitsfunc.write_map('./ttt.fits', m, fits_IDL=False, overwrite=True, coord='C')

plt.show()
