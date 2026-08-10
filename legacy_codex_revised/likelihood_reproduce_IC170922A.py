#!/usr/bin/python
import astropy.io.fits as pf
from numpy import *
from scipy import integrate
from scipy import interpolate as intp
import matplotlib.pyplot as plt 
import os,datetime
import use
#set_printoptions(suppress=True)
#start_time = datetime.datetime.now() 
#print datetime.datetime.now() - start_time

#####################################  ######################################
hbarc = 0.197326978 # GeVfm
sin2weakangle = 0.2223
alpha = 1/137.035999139; GF = 1.1663787e-5; e = 0.302822120811;
m_p = 0.93827231; m_n = 0.93956563; m_e = 0.5109906e-3; m_mu = 0.1056583745; m_tau = 1.77682
m_W = 80.385; m_Z = 91.1876
GeV2cm2 = 3.893793625E-28

# TXS_l = 195.405388; TXS_b = -19.636034 Should not use this one, cuz this is not the direction of the IceCube events.
nu_RA = 77.43; nu_Dec = 5.72; # 170922A
nu_l = 195.420673; nu_b = -19.561067 # converted from above 
sgm_nu = 0.25 # use the number of Table S1.              #!
sgm_nu = 0.15 # True value, highly likely.
#???
#################################### !! #####################################


# Reproduce IceCube results.

f = pf.open('./data_input/gll_psc_v16.fit')
l_3FGL = f[1].data.field('GLON')
b_3FGL = f[1].data.field('GLAT')
f1 = pf.open('./data_input/gll_psch_v13.fit')
l_3FHL = f1[1].data.field('GLON')
b_3FHL = f1[1].data.field('GLAT')
#print f[1].data[565]
#print f1[1].data[328]

spatial_fac = 1./(2*pi*sgm_nu**2)*exp( -( (l_3FGL-nu_l)**2 + (b_3FGL-nu_b)**2 )/(2*sgm_nu**2) )
#spatial_fac = 1./(2*pi*sgm_nu**2)*exp( -( (l_3FHL-nu_l)**2 + (b_3FHL-nu_b)**2 )/(2*sgm_nu**2) )

W_acc = 1.0417 #!

S = spatial_fac.sum()*W_acc
#print 'S', S


############################### Background PDF ################################
tmp = loadtxt('data_input/1601.06484_Fig9_right.dat').T

#print integrate.simps(tmp[1], tmp[0]) # checked below and it's correct...
area = integrate.simps(tmp[1], tmp[0])
##print integrate.trapz(tmp[1], tmp[0])
tmp1 = intp.interp1d(tmp[0], tmp[1]/area/2./pi, kind='linear', bounds_error=False, fill_value=0) # correct

tmp2 = tmp1(-0.1)

B = tmp2 #!
print B
############################## !Background PDF! ###############################

TS = 2*log( S/B  )
#print sqrt(TS)
#print S
#print B
TS = 2*log( S/B  )
print sqrt(TS)




#def S():
    #spatial_fac = 1./(2*pi*sgm_nu**2)*exp( -( ( -nu_l)**2+( -nu_b)**2 )/(2*sgm_nu**2) )  # Not finished
    #weight_fac = 
    #acceptance_fac = 
    #return 0

#L = 2*log(S/B)

