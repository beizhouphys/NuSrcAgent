#!/usr/bin/python
# -*- coding:utf-8 -*- 
import astropy.io.fits as pf
from numpy import *
import numpy as np
#from scipy import integrate
#from scipy import interpolate as intp
import matplotlib.pyplot as plt 
import os,datetime
import use
# set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=3, floatmode='maxprec')
#start_time = datetime.datetime.now() 
#print datetime.datetime.now() - start_time


import astropy.coordinates as coord
from astropy.io import ascii
import astropy.units as u
d2r = 180./pi

#####################################  ######################################
#################################### !! #####################################

# 不要老保存...


# bin in RA and Dec
'''
from source_copy import *
from neutrinos_data import *

fig = plt.figure(figsize=(13,6.5))
ax = fig.add_subplot(111, projection="mollweide")

N_Decs = 180
N_RAs = 360
nus  = zeros( (N_Decs, N_RAs) )
Decs = linspace(-90, 90, N_Decs+1)/d2r
RAs  = linspace(0,  360, N_RAs+1)/d2r

#RAs_c = RAs[:-1]/2. + RAs[1:]/2.
#Decs_c = Decs[:-1]/2. + Decs[1:]/2.
RAs_2D, Decs_2D = np.meshgrid( RAs, Decs )


for k in range( len(Nks) ): # This is much faster than above
    RAs_nu1D  = RAs_nu[k, 0:Nks[k]]
    Decs_nu1D = Decs_nu[k, 0:Nks[k]]
    #tmp = where( (RAs_nu1D>RAs[j])*(RAs_nu1D<RAs[j+1])*(Decs_nu1D>Decs[i])*(Decs_nu1D<Decs[i+1]) )[0]
    #nus[i,j] += len(tmp) 
    nus += histogram2d(Decs_nu1D, RAs_nu1D, bins=(Decs, RAs))[0]
print(nus.max()) # 73

import matplotlib.colors as colors
#use.printA(nus)
#use.printA(nus.sum())
#exit()

#c = ax.pcolormesh( RAs_2D-180./d2r, Decs_2D, nus, cmap='Blues', alpha=1. )
c = ax.pcolormesh( RAs_2D-180./d2r, Decs_2D, nus, cmap='Blues', norm=colors.SymLogNorm(linthresh=1., linscale=1., base=10, vmin=1, vmax=100.), edgecolors='face' ) # alpha = 1
#plt.colorbar(c)
cb = plt.colorbar(c, fraction=0.025, pad=0.04)
cb.ax.tick_params(labelsize=18)

ax.scatter(RAs_src-180/d2r, Decs_src, c='crimson', s=2.5)


ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=18)
ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=18)

#ax.set_yticks([90/d2r, 75/d2r])
#ax.set_yticklabels([r'$90\circ$', r'$75\circ$'])
#ax.set_xticklabels(['14h','16h','18h','20h','22h','0h','2h','4h','6h','8h','10h'])
#ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
ax.grid(True)

plt.savefig('./Tex_20201030_HEnu_radio_quasars/skymap.pdf',bbox_inches='tight', pad_inches=0.1)
plt.show()
'''


# bin in RA and sin(Dec)
from source import *
from neutrinos_data import *

print('Remember to include events with |Dec| > 87 deg !!!!')

fig = plt.figure(figsize=(13,6.5))
ax = fig.add_subplot(111, projection="mollweide")

N_Decs = 180
N_RAs = 360
nus  = zeros( (N_Decs, N_RAs) )
#Decs = linspace(-90, 90, N_Decs+1)/d2r
Decs = arcsin( linspace(-1, 1, N_Decs+1) )
#print(Decs)
#exit()
RAs  = linspace(0,  360, N_RAs+1)/d2r


#RAs_c = RAs[:-1]/2. + RAs[1:]/2.
#Decs_c = Decs[:-1]/2. + Decs[1:]/2.
RAs_2D, Decs_2D = np.meshgrid( RAs, Decs )


for k in range( len(Nks) ): 
    RAs_nu1D  = RAs_nu[k, 0:Nks[k]]
    Decs_nu1D = Decs_nu[k, 0:Nks[k]]
    #tmp = where( (RAs_nu1D>RAs[j])*(RAs_nu1D<RAs[j+1])*(Decs_nu1D>Decs[i])*(Decs_nu1D<Decs[i+1]) )[0]
    #nus[i,j] += len(tmp) 
    nus += histogram2d(Decs_nu1D, RAs_nu1D, bins=(Decs, RAs))[0]
print(nus.max()) # 57
print(nus.min()) # 1

import matplotlib.colors as colors


c = ax.pcolormesh( RAs_2D-180./d2r, Decs_2D, nus, cmap='Blues', norm=colors.SymLogNorm(linthresh=1., linscale=1., base=10, vmin=1, vmax=60.), edgecolors='face' ) # alpha = 1
#c = ax.pcolormesh( RAs_2D-180./d2r, Decs_2D, nus, cmap='Oranges', norm=colors.SymLogNorm(linthresh=1., linscale=1., base=10, vmin=1, vmax=60.), edgecolors='face' ) # alpha = 1
#plt.colorbar(c)
cb = plt.colorbar(c, fraction=0.025, pad=0.04, 
                 ticks=[1,2,3,4,5,6,7,8,9,10,20,30,40,50,60])
cb.ax.set_yticklabels(['1','','','','','','','','','10','','','','','60'])  # horizontal colorbar
cb.ax.tick_params(labelsize=18)
cb.set_label('Number of neutrino events per bin', size=18)

ax.scatter(RAs_src-180/d2r, Decs_src, c='crimson', s=2.5)
#ax.scatter(RAs_src-180/d2r, Decs_src, c='b', s=2.5)
#ax.scatter(RAs_src-180/d2r, Decs_src, s=2.5, facecolors='none', edgecolors='crimson')


ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=18)
ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=18)

#ax.set_yticks([90/d2r, 75/d2r])
#ax.set_yticklabels([r'$90\circ$', r'$75\circ$'])
#ax.set_xticklabels(['14h','16h','18h','20h','22h','0h','2h','4h','6h','8h','10h'])
#ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
ax.grid(True)

#plt.savefig('./Tex_20201030_HEnu_radio_quasars/skymap.pdf',bbox_inches='tight', pad_inches=0.1)
#plt.savefig('./Tex_20201030_HEnu_radio_quasars/skymap.jpg',bbox_inches='tight', pad_inches=0.1)
plt.show()


#backup
