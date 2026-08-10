#!/usr/bin/python
import astropy.io.fits as pf
from numpy import *
from scipy import integrate
from scipy import interpolate as intp
import matplotlib.pyplot as plt 
import os,datetime
import use
#set_printoptions(suppress=True, linewidth=1000, threshold=None, precision=5, floatmode='maxprec')
#start_time = datetime.datetime.now() 
#print datetime.datetime.now() - start_time

'#################################  ##################################'
'################################ !! #################################'
d2r = 180./pi


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

gamma = -2.0
EAfilenms = array(['data_input/IceCube_data_released/Search_for_point_sources_with_first_year_of_IC86_data/TabulatedAeff.txt'])
tmp = loadtxt(EAfilenms[0])
Es = sqrt( unique(tmp[:,0]) * unique(tmp[:,1]) )
coszeniths =  unique(tmp[:,2])/2. + unique(tmp[:,3])/2.
Aeff = tmp[:,4]
Aeff = Aeff.reshape( -1, len(coszeniths) ) # (70, 200)

# switch here for different directions #!
#Aeff = sum(Aeff[:, 0:10], axis=1)/10. # 0:10   -> zenith -1 -- -0.9
Aeff = sum(Aeff[:, 90:100], axis=1)/10.   # 90:100 -> zenith -0.1 -- 0.0

Aeff_intp = intp.interp1d( log(Es), log(Aeff), kind='linear', bounds_error=False, fill_value=-inf) 


# Calc E pdf
dat_3D = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_I_smearing_3D_BZ.dat')
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
lgEmus = linspace( 0., 10., 1+100 ); Emus = 10**lgEmus #
Enu_C = 10**( (lgEnu_L+lgEnu_R)/2. )

dat_3D_tmp = dat_3D_H #! switch here for different directions.
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
Aeff2 = exp( Aeff_intp(log(Enu_C)) ); Aeff2 = Aeff2.reshape(-1,1)

flux = (Enu_C**(gamma+1.)).reshape(-1,1) #! switch here for either PL for atm nu flux
#flux = exp(atm_numu_intp(log(Enu_C)))*Enu_C; flux=flux.reshape(-1,1)

Epdf_H = integrate.simps( PDF_Emu_Enu*Aeff2*flux, log(Enu_C), axis=0 ) \
        # prob. density in lgEmu to in Emu, not normalized  
        # PDF_Emu_Enu (14, 101); 14 is the size of Enu_C 
norm = integrate.simps( Epdf_H, lgEmus ) # stable, int in log gives the same result as int in linear 
Epdf_H /= norm # normalized 
#savetxt('data_output_new_data/tmp2.txt', array([ Emus, Epdf_H ]).T)


for i in range(0): # check the interpolation, good # the use of this part?
    fig = plt.figure(figsize=(6, 4), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('linear'); ax.set_yscale('linear')
    clrs = ['b','purple','r','orange','y']; i_clr = 0
    
    dat_3D_S1 = zeros( (len(lgEnu_L), len(lgEmus)) )
    for i in range( len(lgEnu_L) ):
        tmp_dat_3D_Enu = dat_3D_S[ where( dat_3D_S[:,0]==lgEnu_L[i] ) ]
        if len( tmp_dat_3D_Enu ) != 20.: # check
            print('errir') 
        lgEmus_Enu = (tmp_dat_3D_Enu[:,4] + tmp_dat_3D_Enu[:,5])/2
        tmp_intp = intp.interp1d( lgEmus_Enu, tmp_dat_3D_Enu[:,6], kind='linear', bounds_error=False, fill_value=0)
        dat_3D_S1[i] = tmp_intp(lgEmus)  # checked
    
        if lgEnu_L[i] == 2.0 or lgEnu_L[i] == 3.5 or lgEnu_L[i] == 5.0 or lgEnu_L[i] == 6.5 or lgEnu_L[i] == 8.0: # only bins shown in fig.4
            ax.plot(lgEmus,  dat_3D_S1[i],'-',c=clrs[i_clr],lw=1.5,ms=2) 
            i_clr += 1
    
    #ax.set_xlabel(r"$E$  [ GeV ]",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
    #ax.set_ylabel(r"$E^2dN/dE$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]",fontsize=20)
    ax.set_xlim(0,10)
    ax.set_ylim(0,0.6)
    ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
    plt.grid()#ls='-', lw=0.5)
    plt.show()

# '''
fig = plt.figure(figsize=(6, 6), facecolor='w')
ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
ax.set_xscale('log'); ax.set_yscale('log')

for i in range(1): # To compare my SEpdfs with Nicolas ppr
    ax.plot(Emus, Epdf_H,'r-',label=r'H',lw=1.5,ms=2) 
    tmp = loadtxt( 'data_input/1706.02175_fig2_left_Spdf.dat' ).T
    ax.plot(tmp[0], tmp[1],'c--',label=r'',lw=1.5,ms=2) 
    tmp = loadtxt( 'data_input/1706.02175_fig2_right_Spdf.dat' ).T
    ax.plot(tmp[0], tmp[1],'g--',label=r'',lw=1.5,ms=2) 

for i in range(0): # Compare the two ways of calc bkgd pdf and with Nicolas; North
    ax.plot(Emus, Epdf_H,'b-',label=r'BkgdEpdf H, flux+EA+smearing',lw=1.5,ms=2) 
    tmp = loadtxt( 'data_input/1706.02175_fig2_left_Bpdf.dat' ).T
    ax.plot(tmp[0], tmp[1],'g--',label=r'BkgdEpdf N, Nicolas',lw=1.5,ms=2) 
for i in range(0): # Compare the two ways of calc bkgd pdf and with Nicolas; Horizontal
    ax.plot(Emus, Epdf_H,'r-',label=r'BkgdEpdf H, flux+EA+smearing',lw=1.5,ms=2) 
    tmp = loadtxt( 'data_input/1706.02175_fig2_right_Bpdf.dat' ).T
    ax.plot(tmp[0], tmp[1],'g--',label=r'BkgdEpdf H, Nicolas',lw=1.5,ms=2) 
    tmp1 = loadtxt('data_output_new_data/bkgd_Epdf_IC86a_horizontal_to_cmpr_1706.dat').T
    ax.plot(tmp1[0], tmp1[1], 'k-',label=r'BkgdEpdf H, from data',lw=1.5,ms=2) 
for i in range(0): # compare the ratio for the horizontal
    tmp_intp = intp.interp1d( log(Emus), log(Epdf_H), kind='linear', bounds_error=False, fill_value=-inf)
    tmp1 = loadtxt('data_output_new_data/bkgd_Epdf_IC86a_horizontal_to_cmpr_1706.dat').T
    ax.plot(tmp1[0], exp( tmp_intp(log(tmp1[0])) )/tmp1[1], 'k-',label=r'ratio',lw=1.5,ms=2) 
    tmp2 = loadtxt( 'data_input/1706.02175_fig2_right_Spdf.dat' ).T
    tmp3 = loadtxt( 'data_input/1706.02175_fig2_right_Bpdf.dat' ).T
    xs, ys = use.org_data( [tmp2[0], tmp3[0] ], [tmp2[1], tmp3[1]], nlogbins=10 ) 
    ys1 = ys[0]/ys[1]
    ax.plot(xs, ys1, 'k--',label=r'ratio',lw=1.5,ms=2) 

ax.set_xlabel(r"$E_\mu$  [ GeV ]",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
#ax.set_ylabel(r"$E^2dN/dE$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]",fontsize=20)
ax.set_xlim(1e1,1e6)
#use.autoscale_y(ax)
ax.set_ylim(1e-4,2e0)
ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
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
plt.grid()#ls='-', lw=0.5)
plt.show()
# '''


# Plot and compare with Fig.4 of the paper
for i in range(1):
    fig = plt.figure(figsize=(6, 4), facecolor='w')
    ax = fig.add_axes([0.145, 0.12, 0.82, 0.82 ])
    ax.set_xscale('linear'); ax.set_yscale('linear')
    
    smearing_3D_North = smearing_3D[ where(smearing_3D[:,2] == -90.) ] #south
    #smearing_3D_North = smearing_3D[ where(smearing_3D[:,2] == -10.) ] #horizon
    #smearing_3D_North = smearing_3D[ where(smearing_3D[:,2] == 10.) ] #north

    clrs = ['b','purple','r','orange','y']; i_clr = 0
    for i in range( len(lgEnu_L) ):
        if lgEnu_L[i] == 2.0 or lgEnu_L[i] == 3.5 or lgEnu_L[i] == 5.0 or lgEnu_L[i] == 6.5 or lgEnu_L[i] == 8.0: # only bins shown in fig.4
            tmp_E_Dec = smearing_3D_North[ where( smearing_3D_North[:,0]==lgEnu_L[i] ) ] # (20, 7)
            xxx = sort(concatenate( (tmp_E_Dec[:,4], tmp_E_Dec[:,5]) )) 
            yyy = repeat(tmp_E_Dec[:,6],2) 
            ax.plot(xxx, yyy,'-',label=r'',c=clrs[i_clr],lw=1.5,ms=2) 
            i_clr += 1
    
    #ax.set_yticks( [0,0.1,0.2,0.3,0.4,0.5,0.6]  )
    #ax.set_xlabel(r"$E$  [ GeV ]",fontsize=20, labelpad=None) #label pad to fix some thing flexibly
    #ax.set_ylabel(r"$E^2dN/dE$  [ GeV cm$^{-2}$ s$^{-1}$ sr$^{-1}$ ]",fontsize=20)
    #ax.set_xlim(0,10)
    #ax.set_ylim(0,0.6)
    #ax.legend(loc='best',prop={'size':14})  # Larger if used for a paper.
    ax.tick_params(axis='both', which='major', direction='in', length = 10, width = 1.5, labelsize=20)
    ax.tick_params(axis='x', pad=6) # for numbers with superscript, 6 is from adjusting to match y axis
    ax.tick_params(axis='both', which='minor', direction='in', length = 5, width = 1, labelsize=20)
    plt.grid()#ls='-', lw=0.5)
    plt.show()


exit()



#backup

for i in range(0): # some quick look at the data
    dat_all = loadtxt('./data_input/IceCube_data_released/icecube_10year_ps/irfs/IC86_II_smearing.csv')
    print( dat_all.shape ) # (369600, 11)
    lgEnu_L = unique(dat_all[:,0]) \
            # [2.  2.5 3.  3.5 4.  4.5 5.  5.5 6.  6.5 7.  7.5 8.  8.5]; 14 bins
    lgEnu_R = unique(dat_all[:,1])  \
            # [2.5 3.  3.5 4.  4.5 5.  5.5 6.  6.5 7.  7.5 8.  8.5 9. ];
    Dec_L = unique(dat_all[:,2]) # [-90. -10.  10.]
    Dec_R = unique(dat_all[:,3]) # [-10.  10.  90.]
    #Emu_edgesL = unique(dat_all[:,4]) # Binning not universal \
            # Readme: In order to reduce statistical uncertainties in each 5D bin, bins are selected in each (E_nu, Dec_nu) bin independently.
    #Emu_edgesR = unique(dat_all[:,5])
    AngErr_edgesL = unique(dat_all[:,8]) # Binning not universal
    AngErr_edgesR = unique(dat_all[:,9])
    print( dat_all[:,10].sum() ) # Sum of frational counts is 42, = 14*3 
    exit()
    
    tmp_E_Dec = dat_all[ where( dat_all[:,0]==2. ) ] 
    #print(tmp_E_Dec)
    #print(tmp_E_Dec.shape) # (26400, 11);  369600/26400=14 = num of Ebins
    
    tmp2 = tmp_E_Dec[ where( tmp_E_Dec[:,2]==-90. ) ]
    print(tmp2)
    print(tmp2.shape) # (8800, 11); 26400/8800=3 = num of Dec bins
    Emu_edgesL = tmp2[:,4]
    Emu_edgesR = tmp2[:,5]

