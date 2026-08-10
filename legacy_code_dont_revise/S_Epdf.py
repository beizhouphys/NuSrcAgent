#!/usr/bin/python
import astropy.io.fits as pf
from numpy import *
from scipy import integrate
from scipy import interpolate as intp
import matplotlib.pyplot as plt 
import os,datetime
import use
import sys
#set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=5, floatmode='maxprec')
#start_time = datetime.datetime.now() 
#print datetime.datetime.now() - start_time

'#################################  ##################################'
'################################ !! #################################'
d2r = 180./pi

'################################# Input ##################################'
#gamma = -2.0 #!
#gamma = -2.5 #!
#gamma = -3.0 #!
#gamma = -3.1 #!
#gamma = None #!
gamma = float(sys.argv[1]) #!
print('gamma', gamma)

#phase = 'IC40' ##!!
#phase = 'IC59'
#phase = 'IC79'
#phase = 'IC86a'
#phase = 'IC86b'
phase = sys.argv[2] #!
print('phase', phase)


' Realistic spectra '
if gamma == None:
    pass
    #E2dNdE
    #spec = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/realistic_spectra/1306.2274_Fig_4_thick_dotted_ULGRB.txt').T  # extrpolation to > 2e7 GeV look good.
    #spec = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/realistic_spectra/1306.2274_Fig_4_thin_black_LLGRB.txt').T     # extrpolation to > 1e9 GeV look good.
    #spec = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/realistic_spectra/1512.08513_Fig_3_red.txt').T # extrpolation between 1e2 and 1e3 GeV is good.
    #spec = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/realistic_spectra/2002.10575_Fig_6_black_pi_mu_cooling.txt').T   # extrpolation between 1e2 and 1e3 GeV is good.
    #spec = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/realistic_spectra/2002.10575_Fig_6_blue_nu_attn.txt').T  # extrpolation between 1e2 and 1e3 GeV is good.
    #spec[1] = spec[1]/spec[0] # convert from E2dNdE to EdNdE  #############!!!!!!!!!!!!!!!
    
    # dNdE
    #spec = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/realistic_spectra/single_burst_nu_spec/sb_13_LLGRB_prompt.txt').T; spec = spec[[0,2],:];
    #spec = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/realistic_spectra/single_burst_nu_spec/sb_13_ULGRB_CS.txt').T; spec = spec[[0,2],:];
    #spec = loadtxt('../Z_Done_20210323_cjSN/20210300_cjSN/data_input/realistic_spectra/single_burst_nu_spec/sb_15_LLGRB_CJ.txt').T; spec = spec[[0,2],:];
    ###spec = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/realistic_spectra/single_burst_nu_spec/sb_20_nu_attn.txt').T; spec = spec[[0,2],:];
    ###spec = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/realistic_spectra/single_burst_nu_spec/sb_20_nu_attn_new.txt').T; spec = spec[[0,2],:];
    ###spec = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/realistic_spectra/single_burst_nu_spec/sb_20_pm_cool.txt').T; spec = spec[[0,2],:];
    
    #spec[1] = spec[1]*spec[0] # convert from dNdE to EdNdE

'################################ !Input! #################################'

'######################## Read realistic spectra  #########################'
if gamma == None:
    spec_intp = intp.interp1d( log(spec[0]), log(spec[1]), kind='linear', bounds_error=False, fill_value='extrapolate')
    def spec_func(tmpE):
        return exp(spec_intp(log(tmpE)))
    for i in range(0): # test the extrapolation
        fig = plt.figure(figsize=(6, 6), facecolor='w')
        ax = fig.add_axes([ 0.145, 0.12, 0.82, 0.82 ])
        ax.set_xscale('log'); ax.set_yscale('log')
        #ax.set_xscale('linear');
        #ax.set_yscale('linear')
    
        tmpE = use.ebs(1e2,1e9,700)
        ax.plot( tmpE, spec_func(tmpE), 'b-', label=r'', lw=1.5, ms=3) 
        ax.plot( spec[0], spec[1], 'r--', label=r'', lw=1.5, ms=3) 
        
        #ax.errorbar( , , xerr=None, yerr=, fmt='bo', capsize=2, ms=4) 
        #ax.set_xlabel(r"$E$  [ GeV ]",fontsize=20, labelpad=None) #
        #ax.set_ylabel(r"$E^2dN/dE$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]",fontsize=20)
        ax.set_xlim()
        use.autoscale_y(ax)
        ax.set_ylim()
        #ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
        ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=22)
        ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
        ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=22)
        plt.grid()#ls='-', lw=0.5)
        for axis in ['top','bottom','left','right']:
          ax.spines[axis].set_linewidth(1.4)
        #plt.savefig('',,bbox_inches='tight', pad_inches=0.1)
        for i in range(1):
            # fix the issue of ticks missing when axis range > 10 decades
            import matplotlib.ticker
            #Basically know how it works, not totally
            #Used locmaj_x, _y different because problem happens when using same
            locmaj_x = matplotlib.ticker.LogLocator(base=10.0, subs=(1.0, ), numticks=100)
            locmin_x = matplotlib.ticker.LogLocator(base=10.0, subs=arange(2, 10) * .1,
                    numticks=100)
            ax.xaxis.set_major_locator(locmaj_x)
            ax.xaxis.set_minor_locator(locmin_x)
            ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    
            locmaj_y = matplotlib.ticker.LogLocator(base=10.0, subs=(1.0, ), numticks=100)
            locmin_y = matplotlib.ticker.LogLocator(base=10.0, subs=arange(2, 10) * .1,
                    numticks=100)
            ax.yaxis.set_major_locator(locmaj_y)
            ax.yaxis.set_minor_locator(locmin_y)
            ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        plt.show()
        exit()
    
'####################### !Read realistic spectra ! ########################'


for i in range(0): # Simplify the smearing file and output
    dat_all = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC40_smearing.csv')
    #dat_all = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC59_smearing.csv')
    #dat_all = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC79_smearing.csv')
    #dat_all = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_I_smearing.csv')
    #dat_all = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_II_smearing.csv')
    
    print( dat_all.shape ) # (369600, 11)
    lgEnu_L = unique(dat_all[:,0]) \
            # [2.  2.5 3.  3.5 4.  4.5 5.  5.5 6.  6.5 7.  7.5 8.  8.5]; 14 bins
    lgEnu_R = unique(dat_all[:,1])  \
            # [2.5 3.  3.5 4.  4.5 5.  5.5 6.  6.5 7.  7.5 8.  8.5 9. ];
    Dec_L = unique(dat_all[:,2]) # [-90. -10.  10.]
    Dec_R = unique(dat_all[:,3]) # [-10.  10.  90.]
    
    smearing_3D = zeros( ( len(lgEnu_L)*len(Dec_L)*20, 7) ) # 20 is bcuz Emu are in 20 bins for all
    ii = 0
    for i in range( len(Dec_L) ): # for each Dec bin
        for j in range( len(lgEnu_L) ): # for each energy bin
            tmp_E_Dec = dat_all[ where( (dat_all[:,0]==lgEnu_L[j]) * (dat_all[:,2]==Dec_L[i]) ) ]
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
                #exit()
                #print( lgEnu_L[j], lgEnu_R[j], Dec_L[i], Dec_R[i], Emu_edgesL[k], Emu_edgesR[k], tmp_E_Dec_Emu[:,10].sum()  )
                smearing_3D[ii] = array([ lgEnu_L[j], lgEnu_R[j], Dec_L[i], Dec_R[i], Emu_edgesL[k], Emu_edgesR[k], tmp_E_Dec_Emu[:,10].sum() ])
                ii = ii +1
    
    print( smearing_3D.shape ) # 840 = 20*3*20; 7 = 2+2+2+1
    #print( smearing_3D[:,-1].sum() ); print( dat_all[:,-1].sum() ) # compare
    
    #savetxt( './data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_II_smearing_3D_BZ.dat', smearing_3D, fmt='%f' )
    savetxt( './data_input/IceCube_data_released/icecube_10year_ps/irfs/tmp.dat', smearing_3D, fmt='%f' )
    #exit()

'############################ Atm nu _flux ############################'
# Get the atm mu _flux, convolve EA and smearing of S_Epdf and see if I get bkgd pdf.  Basically testing my method.
atm = loadtxt('data_input/HKKM2015_spl-ally-20-01-solmin.dat')
atm_numu = (atm[:,1] + atm[:,1])/2.
atm_numu = atm_numu.reshape(20,-1) \
        # (20, 101); 20 zeniths, 101 Es
atm_numu1 = atm_numu[19]  #!\
        # 10: zenith -0.1 to 0.0
        # 20: zenith -1.0 to -0.9
Es_atm = unique( atm[:,0] )
atm_numu_intp = intp.interp1d( log(Es_atm), log(atm_numu1), kind='linear', bounds_error=False, fill_value=-inf) 
'########################### !Atm nu _flux! ###########################'


'####################### Calc SEpdf ########################'
# Copied from code below and modified.

def Aeff_cosz1(cosz): # get the E dep EA for a cosz; for IC86_I old data only
    #'Just pick the nearest cosz, no interp needed cuz the variation over d(cosz)=0.01 is small.'
    #'Return an interpolation function.'
    tmp = loadtxt('data_input/IceCube_data_released/Search_for_point_sources_with_first_year_of_IC86_data/TabulatedAeff.txt') 
    Es = sqrt( unique(tmp[:,0]) * unique(tmp[:,1]) )
    coszeniths = unique(tmp[:,2])/2. + unique(tmp[:,3])/2.
    Aeff = tmp[:,4]
    Aeff = Aeff.reshape( -1, len(coszeniths) ) # (70, 200)
    
    idx1 = abs(coszeniths - cosz).argmin()
    #Aeff = sum(Aeff[:, 0:10], axis=1)/10. #! \
    #Aeff = sum(Aeff[:, 90:100], axis=1)/10. \
            # 0:10 -> zenith -1 -- -0.9
            # 90:100 -> zenith -0.1 -- 0.0
    Aeff = Aeff[:, idx1]
    #print(idx1)
    #print(Aeff)
    idx2 = where(Aeff>0)[0]
    Aeff_intp_ = intp.interp1d( log(Es[idx2]), log(Aeff[idx2]), kind='linear', bounds_error=False, fill_value=-inf) 
    return Aeff_intp_
def Aeff_cosz(cosz): # get the E dep EA for a cosz
    #'Just pick the nearest cosz, no interp needed cuz the variation over d(cosz)=0.01 is small.'
    #'Return an interpolation function.'
    if phase == 'IC40':
        tmp = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC40_effectiveArea.csv') 
    if phase == 'IC59':
        tmp = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC59_effectiveArea.csv') 
    if phase == 'IC79':
        tmp = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC79_effectiveArea.csv') 
    if phase == 'IC86a':
        tmp = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_I_effectiveArea.csv') 
    if phase == 'IC86b':
        tmp = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_II_effectiveArea.csv') 
    Es = sqrt( 10**unique(tmp[:,0]) * 10**unique(tmp[:,1]) )
    #coszeniths = unique( sin( (90.+tmp[:,2])/d2r ) ) + unique( sin( (90.+tmp[:,3])/d2r ) )
    coszeniths = cos( (90.+unique(tmp[:,2]))/d2r )/2. + cos( (90.+unique(tmp[:,3]))/d2r )/2.
    #print(coszeniths)
    Aeff = tmp[:,4]
    Aeff = Aeff.reshape( -1, len(Es) ) # (70, 200)
    Aeff = Aeff.T
    # print( Aeff[:,0] )
    
    idx1 = abs(coszeniths - cosz).argmin()
    #print(coszeniths)
    #Aeff = sum(Aeff[:, 0:10], axis=1)/10. #! \
    #Aeff = sum(Aeff[:, 90:100], axis=1)/10. \
            # 0:10 -> zenith -1 -- -0.9
            # 90:100 -> zenith -0.1 -- 0.0
    #print( idx1 )
    Aeff = Aeff[:, idx1]
    #print( Aeff )
    idx2 = where(Aeff>0)[0]
    Aeff_intp_ = intp.interp1d( log(Es[idx2]), log(Aeff[idx2]), kind='linear', bounds_error=False, fill_value=-inf ) 
    return Aeff_intp_


for i in range(1): # read smearing files and initilize stuff
    # Reaarange the smearing files to dat_3D_S, dat_3D_H, and dat_3D_N.
    if phase == 'IC40':
        dat_3D = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC40_smearing_3D_BZ.dat') 
    if phase == 'IC59':
        dat_3D = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC59_smearing_3D_BZ.dat') 
    if phase == 'IC79':
        dat_3D = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC79_smearing_3D_BZ.dat') 
    if phase == 'IC86a':
        dat_3D = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_I_smearing_3D_BZ.dat') 
    if phase == 'IC86b':
        dat_3D = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_II_smearing_3D_BZ.dat') 
    
    lgEnu_L = unique(dat_3D[:,0]) \
            # [2.  2.5 3.  3.5 4.  4.5 5.  5.5 6.  6.5 7.  7.5 8.  8.5]; 14 bins
    #use.printA( lgEnu_L )  
    lgEnu_R = unique(dat_3D[:,1])  \
            # [2.5 3.  3.5 4.  4.5 5.  5.5 6.  6.5 7.  7.5 8.  8.5 9. ];
    Dec_L = unique(dat_3D[:,2]) # [-90. -10.  10.]
    Dec_R = unique(dat_3D[:,3]) # [-10.  10.  90.], south, horizon, north
    
    dat_3D_S = dat_3D[ where( dat_3D[:,2] == Dec_L[0] ) ]
    #print( dat_3D_S.shape ) # (280, 7)
    dat_3D_H = dat_3D[ where( dat_3D[:,2] == Dec_L[1] ) ]
    dat_3D_N = dat_3D[ where( dat_3D[:,2] == Dec_L[2] ) ]
    
    lgEmus = linspace( 0., 10., 1+100 ); Emus = 10**lgEmus #!
    Enu_C = 10**( (lgEnu_L+lgEnu_R)/2. )

# The functions below are writen in the same way as (and initially copied from) S_Epdf_test.py
def S_E_pdf_N(cosz, lgEpr):
    # Need input from above, 
        # dat_3D_N/dat_3D_H/dat_3D_S, cols: 0, lgEnu_min 1, lgEnu_max; 2 3, Dec min max; 4 5, lgEmu min max; 6: fraction from simulation
        # lgEmus, Emus, Enu_C
    # checked with the prev rslt of cosz = -1 to -0.9
    dat_3D_tmp = dat_3D_N #!

    PDF_Emu_Enu = zeros( (len(lgEnu_L), len(lgEmus)) ) 
        # lgEmu-normalized E pdfs for every Enus; final results of the cycle below.
    for i in range( len(lgEnu_L) ): # For each Enu
        #'Select the smearing matrix for the Enu'
        tmp_dat_3D_Enu = dat_3D_tmp[ where( dat_3D_tmp[:,0]==lgEnu_L[i] ) ] #\
                # (20, 7) # 20 is the # of Emu bins, 7 is lgE_l, lgE_h, Dec_l, Dec_h, lgEmu_l, lgEmu_h, Fraction
                # print( tmp_dat_3D_Enu[:,6].sum() ) # =1 for all, checked

        #'Convert from fraction in each bin to PDF(lgEmu).' 
        tmp_dat_3D_Enu[:, 6] = tmp_dat_3D_Enu[:, 6] / (tmp_dat_3D_Enu[:,5] - tmp_dat_3D_Enu[:,4])  
            # This step may not be necessary cuz the bins are the same size and another normalization is done after interpolation
            #print( tmp_dat_3D_Enu[:,6].sum() ) # =1 for all, checked
        if len( tmp_dat_3D_Enu ) != 20.: # check
            print('error') 
            exit()
    
        lgEmus_Enu = (tmp_dat_3D_Enu[:,4] + tmp_dat_3D_Enu[:,5])/2. # (20,)
        tmp_intp = intp.interp1d( lgEmus_Enu, tmp_dat_3D_Enu[:,6], kind='linear', bounds_error=False, fill_value=0 ) 
        PDF_Emu_Enu[i] = tmp_intp(lgEmus)  # checked 
            # lgEmus is from calc outside the func
            # lgEmus = linspace( 0., 10., 1+100 ); Emus = 10**lgEmus #!
        PDF_Emu_Enu[i] = PDF_Emu_Enu[i]/PDF_Emu_Enu[i].sum()/( lgEmus[2]-lgEmus[1] )    \
                # normalize to pdf(lgEmu)
                # print( dat_3D_H1[i].sum() ) 
    # so now I get pdf(lgEmu) for each specific lg(Enu), PDF_Emu_Enu.

    Aeff_intp = Aeff_cosz(cosz)
    Aeff2 = exp( Aeff_intp(log(Enu_C)) ); Aeff2 = Aeff2.reshape(-1,1)
    if gamma != None:
        spectrum = (Enu_C**(gamma+1.)).reshape(-1,1) # gamma+1 to convert from dNdE to EdNdE
    else:
        spectrum = spec_func(Enu_C).reshape(-1,1)
    #spectrum = exp(atm_numu_intp(log(Enu_C)))*Enu_C; spectrum=spectrum.reshape(-1,1)
    
    Epdf_N= integrate.simps(PDF_Emu_Enu*Aeff2*spectrum,log(Enu_C), axis=0)\
            # prob. density in lgEmu to in Emu, not normalized  #!
            # First term is smearing matrix, second is EA, third is neutrino _spectrum
            # PDF_Emu_Enu (14, 101); 14 is the size of Enu_C 
    norm = integrate.simps( Epdf_N, lgEmus ) # stable, int in log gives the same result as int in linear #!
    Epdf_N /= norm # normalized #!
    tmp_intp1 = intp.interp1d( lgEmus, Epdf_N, kind='linear', bounds_error=False, fill_value=0) 
    return tmp_intp1(lgEpr) 

def S_E_pdf_H(cosz, lgEpr):
    # checked with the prev rslt of cosz = -0.1 to 0.0
    dat_3D_tmp = dat_3D_H #!
    PDF_Emu_Enu = zeros( (len(lgEnu_L), len(lgEmus)) ) 

    for i in range( len(lgEnu_L) ): # For each Enu
        tmp_dat_3D_Enu = dat_3D_tmp[ where( dat_3D_tmp[:,0]==lgEnu_L[i] ) ] #\
                # (20, 7) # 20 is the # of Emu bins, 7 is lgE_l, lgE_h, Dec_l, Dec_h, lgEmu_l, lgEmu_h, Fraction
                # print( tmp_dat_3D_Enu[:,6].sum() ) # =1 for all, checked

        tmp_dat_3D_Enu[:, 6] = tmp_dat_3D_Enu[:, 6] / (tmp_dat_3D_Enu[:,5] - tmp_dat_3D_Enu[:,4])  # Convert from fraction in each bin to PDF(lgEmu). \
                # This step may not be necessary cuz the bins are the same size and another normalization is done after interpolation
                #print( tmp_dat_3D_Enu[:,6].sum() ) # =1 for all, checked
        
        if len( tmp_dat_3D_Enu ) != 20.: # check
            print('error') 
            exit()
    
        lgEmus_Enu = (tmp_dat_3D_Enu[:,4] + tmp_dat_3D_Enu[:,5])/2. # (20,)
        tmp_intp = intp.interp1d( lgEmus_Enu, tmp_dat_3D_Enu[:,6], kind='linear', bounds_error=False, fill_value=0) 
        PDF_Emu_Enu[i] = tmp_intp(lgEmus)  # checked 
        PDF_Emu_Enu[i] = PDF_Emu_Enu[i]/PDF_Emu_Enu[i].sum()/( lgEmus[2]-lgEmus[1] )    \
                # normalize to pdf(lgEmu)
                # print( dat_3D_H1[i].sum() ) 
    # so now I get pdf(lgEmu) for each specific lg(Enu) 

    Aeff_intp = Aeff_cosz(cosz)
    Aeff2 = exp( Aeff_intp(log(Enu_C)) ); Aeff2 = Aeff2.reshape(-1,1)
    if gamma != None:
        spectrum = (Enu_C**(gamma+1.)).reshape(-1,1)
    else:
        spectrum = spec_func(Enu_C).reshape(-1,1)
    #spectrum= exp(atm_numu_intp(log(Enu_C)))*Enu_C; spectrum=spectrum.reshape(-1,1)
    Epdf_H= integrate.simps(PDF_Emu_Enu*Aeff2*spectrum, log(Enu_C), axis=0)\
            # prob. density in lgEmu to in Emu, not normalized  #!
            # PDF_Emu_Enu (14, 101); 14 is the size of Enu_C 
    norm = integrate.simps( Epdf_H, lgEmus ) # stable, int in log gives the same result as int in linear #!
    Epdf_H /= norm # normalized  #!
    tmp_intp1 = intp.interp1d( lgEmus, Epdf_H, kind='linear', bounds_error=False, fill_value=0) 
    return tmp_intp1(lgEpr) 

def S_E_pdf_S(cosz, lgEpr):
    # Need input from above, 
        # dat_3D_N/dat_3D_H/dat_3D_S, cols: 0, lgEnu_min 1, lgEnu_max; 2 3, Dec min max; 4 5, lgEmu min max; 6: fraction from simulation
        # lgEmus, Emus, Enu_C
    # checked with the prev rslt of cosz = -1 to -0.9
    dat_3D_tmp = dat_3D_S #!

    PDF_Emu_Enu = zeros( (len(lgEnu_L), len(lgEmus)) ) 
        # lgEmu-normalized E pdfs for every Enus; final results of the cycle below.
    for i in range( len(lgEnu_L) ): # For each Enu
        #'Select the smearing matrix for the Enu'
        tmp_dat_3D_Enu = dat_3D_tmp[ where( dat_3D_tmp[:,0]==lgEnu_L[i] ) ] #\
                # (20, 7) # 20 is the # of Emu bins, 7 is lgE_l, lgE_h, Dec_l, Dec_h, lgEmu_l, lgEmu_h, Fraction
                # print( tmp_dat_3D_Enu[:,6].sum() ) # =1 for all, checked

        #'Convert from fraction in each bin to PDF(lgEmu).' 
        tmp_dat_3D_Enu[:, 6] = tmp_dat_3D_Enu[:, 6] / (tmp_dat_3D_Enu[:,5] - tmp_dat_3D_Enu[:,4])  
            # This step may not be necessary cuz the bins are the same size and another normalization is done after interpolation
            #print( tmp_dat_3D_Enu[:,6].sum() ) # =1 for all, checked
        if len( tmp_dat_3D_Enu ) != 20.: # check
            print('error') 
            exit()
        lgEmus_Enu = (tmp_dat_3D_Enu[:,4] + tmp_dat_3D_Enu[:,5])/2. # (20,)
        tmp_intp = intp.interp1d( lgEmus_Enu, tmp_dat_3D_Enu[:,6], kind='linear', bounds_error=False, fill_value=0 ) 
        PDF_Emu_Enu[i] = tmp_intp(lgEmus)  # checked 
            # lgEmus is from calc outside the func
            # lgEmus = linspace( 0., 10., 1+100 ); Emus = 10**lgEmus #!
        #print( PDF_Emu_Enu[i] )
        #print( PDF_Emu_Enu[i].sum() )
        #print( lgEmus[2]-lgEmus[1] )
        #print()
        PDF_Emu_Enu[i] = PDF_Emu_Enu[i]/PDF_Emu_Enu[i].sum()/( lgEmus[2]-lgEmus[1] )    \
                # normalize to pdf(lgEmu)
                # print( dat_3D_H1[i].sum() ) 
        # so now I get pdf(lgEmu) for each specific lg(Enu), PDF_Emu_Enu.

    Aeff_intp = Aeff_cosz(cosz)
    Aeff2 = exp( Aeff_intp(log(Enu_C)) ); Aeff2 = Aeff2.reshape(-1,1)
    if gamma != None:
        spectrum = (Enu_C**(gamma+1.)).reshape(-1,1)
    else:
        spectrum = spec_func(Enu_C).reshape(-1,1)
    #spectrum = exp(atm_numu_intp(log(Enu_C)))*Enu_C; spectrum=spectrum.reshape(-1,1)
    
    Epdf_S = integrate.simps(PDF_Emu_Enu*Aeff2*spectrum,log(Enu_C), axis=0)\
            # prob. density in lgEmu to in Emu, not normalized  #!
            # PDF_Emu_Enu (14, 101); 14 is the size of Enu_C 
    norm = integrate.simps( Epdf_S, lgEmus ) # stable, int in log gives the same result as int in linear #!
    Epdf_S /= norm # normalized #!
    tmp_intp1 = intp.interp1d( lgEmus, Epdf_S, kind='linear', bounds_error=False, fill_value=0) #!
    return tmp_intp1(lgEpr) 


for i2 in range(1): # Output a 2D table for S E pdfs, for specific _phase and _spectrum
    coszs_ = linspace(-1, 1, 1000)
    Epr_   = use.ebs(1e1, 1e9, 8*100)
    lgEpr_ = log10( Epr_ )
    rslt = zeros( (len(coszs_), len(lgEpr_)) )
    #print( Epr_ )
    for i in range( len(coszs_) ):
        cosz_ = coszs_[i]
        Dec_  = arccos(cosz_)-90/d2r
        if Dec_ >= 10./d2r:
            rslt_Epdf = S_E_pdf_N(cosz_, lgEpr_)
        elif Dec_ < -10./d2r:
            rslt_Epdf = S_E_pdf_S(cosz_, lgEpr_)
        else:
            rslt_Epdf = S_E_pdf_H(cosz_, lgEpr_)
        #print( rslt_Epdf )
        rslt[i] = rslt_Epdf
        print('Check if normalized,', i, integrate.simps( rslt_Epdf, lgEpr_ ) )
    #savetxt( '../20210323_cjSN/20210300_cjSN/data_output/SEpdfs_table/0ttt_'+phase+'.txt', rslt )
    savetxt( 'data_output/Epdfs/ttt_signal_Epdf_2D_GM'+str(abs(gamma))+'_'+phase+'.txt', rslt )
    exit()

for i2 in range(0): # Calc Epdf for each SN
    ' To calc for another dataset, procedures given in above func.'
    ' For each source, only need one number, which is Dec. '
    #tmp1 = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/rpdc_Senno17/SNe_Ibc_29.txt') 
    if phase == 'IC40':
        #tmp1 = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/10_yr_analysis/SNe_data_IC/SNe_Dec_IC40.txt') \
                # Dec in col 3, in rad
        tmp1 = loadtxt('/Users/beizhou/Dropbox/1acdm/1work_ptnl/20230400_BL_SN_Ic/data_input/SN-List_v2.txt') \
                # Dec in col 3, in deg;
    if phase == 'IC59':
        #tmp1 = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/10_yr_analysis/SNe_data_IC/SNe_Dec_IC59.txt') 
        tmp1 = array([ loadtxt('/Users/beizhou/Dropbox/1acdm/1work_ptnl/20230400_BL_SN_Ic/data_input/SN-List_v2.txt')[0] ]); tmp1[:,3]/=d2r
    if phase == 'IC79':
        #tmp1 = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/10_yr_analysis/SNe_data_IC/SNe_Dec_IC79.txt') 
        tmp1 = loadtxt('/Users/beizhou/Dropbox/1acdm/1work_ptnl/20230400_BL_SN_Ic/data_input/SN-List_v2.txt')[1:3]; tmp1[:,3]/=d2r
    if phase == 'IC86a':
        #tmp1 = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/10_yr_analysis/SNe_data_IC/SNe_Dec_IC86a.txt') 
        tmp1 = loadtxt('/Users/beizhou/Dropbox/1acdm/1work_ptnl/20230400_BL_SN_Ic/data_input/SN-List_v2.txt')[3:6]; tmp1[:,3]/=d2r
    if phase == 'IC86b':
        #tmp1 = loadtxt('/Users/beizhou/Dropbox/1acdm/1work/20210323_cjSN/20210300_cjSN/data_input/10_yr_analysis/SNe_data_IC/SNe_Dec_IC86b.txt') 
        tmp1 = loadtxt('/Users/beizhou/Dropbox/1acdm/1work_ptnl/20230400_BL_SN_Ic/data_input/SN-List_v2.txt')[6:]; tmp1[:,3]/=d2r
    Epr_ = use.ebs(1e2, 1e9, 7*10)
    lgEpr_ = log10( Epr_ )
    rslt = zeros( (len(tmp1)+1, len(lgEpr_)) )
    #print( Epr_ )
    for i in range( len(tmp1) ):
        Dec_ = tmp1[i,3]   #######################!!!!!!!!!!!!!!!!!!!!!!!!!
        cosz_ = -sin(Dec_)
        print( Dec_*d2r )
        if Dec_ >= 10./d2r:
            rslt_Epdf = S_E_pdf_N(cosz_, lgEpr_)
        elif Dec_ < -10./d2r:
            rslt_Epdf = S_E_pdf_S(cosz_, lgEpr_)
        else:
            rslt_Epdf = S_E_pdf_H(cosz_, lgEpr_)
        #print( rslt_Epdf )
        rslt[i] = rslt_Epdf
        print('Check if normalized,', i, integrate.simps( rslt_Epdf, lgEpr_ ) )
    rslt[-1] = Epr_ 
    #savetxt( '../20210323_cjSN/ttt_'+phase+'.txt', rslt )
    savetxt( '/Users/beizhou/Dropbox/1acdm/1work_ptnl/20230400_BL_SN_Ic/data_output/ttt_'+phase+'.txt', rslt )
    exit()

for i2 in range(0): # Calc Epdf for IceCube data
    # took about 100m to run 70k events.
    # To calc for another dataset, need change 1) EA file above 2) smearing matrix file above 3) event file below. Marked as '##!!'.
    #tmp1 = loadtxt('data_input/IceCube_data_released/Search_for_point_sources_with_first_year_of_IC86_data/upgoing_events.txt')
    if phase == 'IC40':
        tmp1 = loadtxt('data_input/IceCube_data_released/icecube_10year_ps/events/IC40_exp.csv')  ##!!
    if phase == 'IC59':
        tmp1 = loadtxt('data_input/IceCube_data_released/icecube_10year_ps/events/IC59_exp.csv')  
    if phase == 'IC79':
        tmp1 = loadtxt('data_input/IceCube_data_released/icecube_10year_ps/events/IC79_exp.csv')  
    if phase == 'IC86a':
        tmp1 = loadtxt('data_input/IceCube_data_released/icecube_10year_ps/events/IC86_I_exp.csv')  
    if phase == 'IC86b':
        tmp1 = loadtxt('data_input/IceCube_data_released/icecube_10year_ps/events/IC86_II2VII_exp_BZ.csv')  
    for i in range( len(tmp1) ):
        Dec_ = tmp1[i,4]/d2r
        cosz_ = -sin(Dec_)
        lgEpr_ = array([ tmp1[i,1] ])
        if Dec_ >= 10./d2r:
            print(i,' ', tmp1[i,4],'  ', lgEpr_[0],' ', S_E_pdf_N(cosz_, lgEpr_)[0] )
        elif Dec_ < -10./d2r:
            print(i,' ', tmp1[i,4],'  ', lgEpr_[0],' ', S_E_pdf_S(cosz_, lgEpr_)[0] )
        else:
            print(i,' ', tmp1[i,4],'  ', lgEpr_[0],' ', S_E_pdf_H(cosz_, lgEpr_)[0] )
    exit()

'###################### !Calc SEpdf! #######################'



#backup

