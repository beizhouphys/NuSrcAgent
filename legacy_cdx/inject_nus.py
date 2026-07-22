#!/usr/bin/python
# -*- coding:utf-8 -*- 
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

'''
First part copied from ns2flux.py and revised
'''

#####################################  ######################################
#################################### !! #####################################

d2r = 180./pi


################################ Atm nu flux #################################
tmp1 = loadtxt('./data_input/HKKM2015_atm_nu_flux_SouthPole_solarMin.dat').T
Enu1 = tmp1[0];
Fnu1 = (tmp1[1]+tmp1[2])*1e-4  # m-2s-1GeV-1sr-1 -> cm-2s-1GeV-1sr-1
Fnu1_intp = intp.interp1d( log(Enu1), log(Fnu1), kind='linear', bounds_error=False, fill_value=-inf)

tmp2 = loadtxt('../20180725_Tridents_HE/data_input/IceCube_6yr_atm.dat').T
Enu2 = tmp2[0];
Fnu2 = tmp2[1]/1.13/Enu2/Enu2 #!
Fnu2_intp = intp.interp1d( log(Enu2), log(Fnu2), kind='linear', bounds_error=False, fill_value=-inf)

def dIdEnu_atm(Enus0):
    'Flux of numu+numubar; Output: GeV-1cm-2s-1sr-1'
    tmp4 = zeros(Enus0.shape)
    idx1 = where(Enus0<=1e4)
    tmp4[idx1] = exp(Fnu1_intp(log(Enus0[idx1])))
    idx2 = where(Enus0>1e4)
    tmp4[idx2] = exp(Fnu2_intp(log(Enus0[idx2])))
    return tmp4
############################### !Atm nu flux! ################################

# Astro nu flux
def dIdEnu(Enus0): # -2.53
    'Flux of numu+numubar; Output: GeV-1cm-2s-1sr-1'
    'Use the measured results by IC coll, in 2001.09520'
    return 1.66e-18*(Enus0/1e5)**(-2.53) #!


EAfilenms = array([ 
    './data_input/IceCube_data_released/icecube_10year_ps/irfs/IC40_effectiveArea.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/irfs/IC59_effectiveArea.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/irfs/IC79_effectiveArea.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_I_effectiveArea.csv',
    './data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_II_effectiveArea.csv',
    ])
Ntots = array([ 36843., 106980.,  93107., 135874., 760639.])


# uptime
for j in range(1):
    uptime_flms = array([
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC40_exp.csv',\
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC59_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC79_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_I_exp.csv',
        './data_input/IceCube_data_released/icecube_10year_ps/uptime/IC86_II2VII_exp_BZ.csv',
        ]) #!
    
    uptimes = zeros( len(uptime_flms) );
    for i in range(len(uptime_flms)):
        tmp = loadtxt(uptime_flms[i])
        uptimes[i] = sum(tmp[:,1]-tmp[:,0])


n_s_astros = zeros( len(Ntots) )
Enus = use.ecs(1e2, 1e9, 14); # same binning as irfs
Enus_b = use.ebs(1e2, 1e9, 14); # same binning as irfs
dNsdEnu = zeros( ( len(Ntots), len(Enus) ) )
for i in range( len(Ntots) ):
    tmp = loadtxt(EAfilenms[i]); Ntot = float(Ntots[i]); uptime = uptimes[i]
    
    Es = 10**( unique(tmp[:,0] )/2.+unique( tmp[:,1])/2. )
    coszeniths = ( cos(90./d2r + unique(tmp[:,2])/d2r) + cos(90./d2r + unique(tmp[:,3])/d2r) )/2.
    Aeff = tmp[:,4]
    Aeff = Aeff.reshape( len(coszeniths),-1 )
    Aeff = sum(Aeff, axis=0)/50. #50 is to normalize 
    idx = where( Aeff>0 ); Aeff=Aeff[idx]; Es=Es[idx];
    Aeff_intp =  intp.interp1d( log(Es), log(Aeff), kind='linear', bounds_error=False, fill_value='extrapolate')  \
            # only increase by ~0.02 compared to above for IC86b.  Later might look into this ########!!!!!!!!!!!!!!!!!!!!!!!
    
    Aeff = exp( Aeff_intp(log(Enus)) )
    
    # Calc
    # for atm nu, to cmpr w/ dat and get scaling factor
    dNdEnu =  Aeff* dIdEnu_atm(Enus) * uptime*24*3600 *4*pi; 
    EdNdEnu = dNdEnu*Enus; Emus = Enus*0.75 # checked # didn't affect rslt much.
    idx = where(Emus>0.) # no different from using 0. #!

    ns_atm = integrate.simps(EdNdEnu[idx], log(Emus[idx]))
    #print('n_s for atm nu:', ns_atm )
    fac = Ntot/ns_atm
    #print('factor:', fac ) 
    
    dNdEnu =  Enus * Aeff*dIdEnu(Enus)*uptime*24*3600 *4*pi*fac  \
            # should've done an int, but lazy, and tot # only differs by 11%
            # Should * 2.3????????????
    dNsdEnu[i] = dNdEnu

# print( dNsdEnu.sum()*1.15129255 ) \
        # To get the tot number and compare with intgration in ns2flux.py.  1.15129255 is the bin with in ln()
dNsdEnu = dNsdEnu/dNsdEnu.sum()*8845.71 # renorm # better to renorm for each IC phase but lazy
print('#', dNsdEnu.sum(axis=1))

#use.printA(dNsdEnu)


dat_all = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC40_smearing.csv')
#dat_all = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC59_smearing.csv')
#dat_all = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC79_smearing.csv')
#dat_all = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_I_smearing.csv')
#dat_all = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_II_smearing.csv') #!

i_IC = 0 #!

print('#', dat_all.shape ) 
lgEnu_edgesL = unique(dat_all[:,0]) \
        # [2.  2.5 3.  3.5 4.  4.5 5.  5.5 6.  6.5 7.  7.5 8.  8.5]; 14 bins
lgEnu_edgesR = unique(dat_all[:,1])  \
        # [2.5 3.  3.5 4.  4.5 5.  5.5 6.  6.5 7.  7.5 8.  8.5 9. ];
Dec_edgesL = unique(dat_all[:,2]) # [-90. -10.  10.]
Dec_edgesR = unique(dat_all[:,3]) # [-10.  10.  90.]
#sgm_edgesL = unique(dat_all[:,-3]) #  The binning is not the same for all

for i in range( 0 ): # for each energy bin
#for i in range( len(lgEnu_edgesL) ): # for each energy bin
    N_nus_E = dNsdEnu[i_IC, i] # get # of nus in the phase & Ebin
    for j in range( len(Dec_edgesL) ): # for each Dec bin
        # get # of nus in the phase & Ebin & DecBin
        N_nus = N_nus_E*abs(sin(Dec_edgesL[j]/d2r)-sin(Dec_edgesR[j]/d2r) )/2. 
        #print( abs( sin(Dec_edgesL[j]/d2r)-sin(Dec_edgesR[j]/d2r) )/2. )

        tmp_E_Dec = dat_all[ where( (dat_all[:,0]==lgEnu_edgesL[i]) * (dat_all[:,2]==Dec_edgesL[j]) ) ] # (8800, 11)
        #print( tmp_E_Dec[:,-1].sum() ) # So it's normalized in each E--Dec bin.
        #sgm_cs = sgm_edgesL/2.+sgm_edgesR/2.

        tmp_E_Dec = tmp_E_Dec[ where(tmp_E_Dec[:,-1]>0) ] # exclude the bins w/o events
        sgm_edgesL = unique(tmp_E_Dec[:,-3]) 
        sgm_edgesR = unique(tmp_E_Dec[:,-2]) 

        tmp3 = zeros( (len(sgm_edgesL) ,4) ) # a new array to contain the #s
        tmp3[:, 0] = sgm_edgesL
        tmp3[:, 1] = sgm_edgesR
        for k in range( len(sgm_edgesL) ):
            'This is to merge the numbers in the same sgm bins'
            #print( sgm_edgesL[k] )
            tmp_E_Dec_sgm = tmp_E_Dec[ where(tmp_E_Dec[:,-3]==sgm_edgesL[k]) ]
            tmp3[k, 2] = tmp_E_Dec_sgm[:,-1].sum() # merge the numbers
            tmp3[k, 3] = tmp3[k, 2]*N_nus # get the counts
            print( tmp3[k, 0], tmp3[k, 1], tmp3[k, 2], tmp3[k, 3] )

        #print( tmp3[:,2].sum() ) # checked if adds up to one.
        #for k in range( tmp_E_Dec.shape[0] ): # delete later.
        #    print( tmp_E_Dec[k, -3], tmp_E_Dec[k, -2], tmp_E_Dec[k, -1], tmp_E_Dec[k, -1]*N_nus )
        #exit()


#dat_simu = loadtxt('./data_output_new_data_inj/IC86b.dat').T
#ang_errs = dat_simu[0]/2. + dat_simu[1]/2.
#PDFs = dat_simu[3] / dat_simu[3].sum()
#CDFs = cumsum(PDFs)
#
#intp0 = intp.interp1d( CDFs, ang_errs, kind='linear', bounds_error=False, fill_value='extrapolate') 
#angerrs = intp0( random.rand(5718) ) #!






exit()


'''
smearing_3D = zeros( ( len(lgEnu_edgesL)*len(Dec_edgesL)*20, 7) ) # 20 is bcuz Emu are in 20 bins for all
ii = 0
for i in range( len(lgEnu_edgesL) ): # for each energy bin
    for j in range( len(Dec_edgesL) ): # for each Dec bin
        tmp_E_Dec = dat_all[ where( (dat_all[:,0]==lgEnu_edgesL[i]) * (dat_all[:,2]==Dec_edgesL[j]) ) ]
        #print(tmp_E_Dec.shape) # (8800,11) for all, correct # 8800=369600/14/3
        Emu_edgesL = unique(tmp_E_Dec[:,4]) # 20 bins for all, but locations vary
        Emu_edgesR = unique(tmp_E_Dec[:,5]) 
        #print( Emu_edgesL.shape )
        #print( Emu_edgesR.shape )
        #print( tmp_E_Dec[:,-1].sum() ) # check the fractional acounts add up to 1.
        #exit()
        for k in range(len(Emu_edgesL)): # for each Emu bin
            tmp_E_Dec_Emu = tmp_E_Dec[ where( tmp_E_Dec[:,4]==Emu_edgesL[k] ) ] 
            #print(tmp_E_Dec_Emu.shape)
            #print( lgEnu_edgesL[i], lgEnu_edgesR[i], Dec_edgesL[j], Dec_edgesR[j], Emu_edgesL[k], Emu_edgesR[k], tmp_E_Dec_Emu[:,10].sum()  )
            smearing_3D[ii] = array([ lgEnu_edgesL[i], lgEnu_edgesR[i], Dec_edgesL[j], Dec_edgesR[j], Emu_edgesL[k], Emu_edgesR[k], tmp_E_Dec_Emu[:,10].sum() ])
            ii = ii +1

print( smearing_3D.shape ) # 840 = 20*3*20; 7 = 2+2+2+1
#print( smearing_3D[:,-1].sum() ); print( dat_all[:,-1].sum() ) # compare

#savetxt( './data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_II_smearing_3D_BZ.dat', smearing_3D, fmt='%f' )
#savetxt( './data_input/IceCube_data_released/icecube_10year_ps/irfs/tmp.dat', smearing_3D, fmt='%f' )
#exit()
'''





exit()




#backup
