#!/usr/bin/python                                                                                  
# -*- coding:utf-8 -*- 
import numpy as np
from numpy import *
from scipy import integrate
from scipy import interpolate as intp
#import matplotlib.pyplot as plt 
import astropy.io.fits as pf
import os
#import healpy as hp 
d2r = 57.29577951308232


'####################  #####################'
'################### !! ####################'


'############# Generating arrays #############'
def arange1(start, end, step):
    return np.arange(start, end + step, step)


def ecs(eb1,eb2,num):
    ebs = np.logspace(log10(eb1),log10(eb2),num+1)
    return np.sqrt(ebs[1:]*ebs[:-1])

def ebs(eb1, eb2, num):
    return np.logspace(log10(eb1),log10(eb2),num+1)

def des(eb1,eb2,num):
    ebs_tmp = ebs(eb1,eb2,num)
    return ebs_tmp[1:] - ebs_tmp[0:-1]

def Des(eb1,eb2,num):
    ebs_tmp = ebs(eb1,eb2,num)
    ecs_tmp = ecs(eb1,eb2,num)
    return ecs_tmp-ebs_tmp[:-1],   ebs_tmp[1:]-ecs_tmp

def ecs1(eb1,eb2,num):
    return ecs(eb1, eb2, int(round( num*np.log10(eb2/eb1) )))

def ebs1(eb1, eb2, num): # num here is number of points per dex
    return ebs(eb1, eb2, int(round( num*np.log10(eb2/eb1) )))

def des1(eb1,eb2,num):
    ebs1_tmp = ebs1(eb1,eb2,num)
    return ebs1_tmp[1:] - ebs1_tmp[0:-1]
'############ !Generating arrays! ############'


'################# Printing out arrays ##################'
'################ !Printing out arrays! #################'


def f2a(func, x):
    'func to array func'
    if isscalar(x) == True:
        return func(x)
    result = np.zeros(len(x))
    for i in range(len(x)):
        result[i] = func(x[i])
    return result

def f2a_2d1(func, x, y):
    'func to array func'
    'The 1st var is array, 2nd is number'
    result = zeros(len(x))
    for i in range(len(x)):
        result[i] = func(x[i],y)
    return result

def f2a_3d1(func, x, y, z):
    'func to array func'
    'The 1st var is array, 2nd and 3rd are numbers'
    #print x
    result = zeros(len(x))
    for i in range(len(x)):
        #print result
        #print result[i]
        #print func(x[i],y,z)
        #print type(func(x[i],y,z))
        result[i] = func(x[i],y,z)
    return result

def f2a_4d1(func, x, y, z, w):
    'func to array func'
    'The 1st var is array, 2nd and 3rd are numbers'
    result = zeros(len(x))
    for i in range(len(x)):
        result[i] = func(x[i],y,z,w)
    return result

def f2a_5d1(func, x, y, z, w, v):
    'func to array func'
    'The 1st var is array, 2nd and 3rd are numbers'
    result = zeros(len(x))
    for i in range(len(x)):
        result[i] = func(x[i],y,z,w,v)
    return result


def d_arr(x):
    return append( append( x[1]-x[0], (x[2:]-x[:-2])/2. ) , x[-1]-x[-2] )

def trapzd1(func,a,b,s,n):
    """ 
    This func is not used for calc a int by trapzd method. This is just used for call several times and add the result of everytime, where the first time gives the two end point values, i.e. 1./2.*(f1+fN)
    follow trapzd of my NR book, P131
    ? don't know why use it, tnm for the same thing...
    """
    if n==1:
        s = 0.5*(b-a)*(func(a)+func(b))
    else:
        it = 2**(n-2)
        tnm = float(it) #!!!!
        h = (b-a)/tnm #h=del in NR
        x = a+0.5*h
        sum = 0.
        for i in range(it):#should write an array version for this in the future
            sum = sum+func(x)
            x = x+h
        #print s,sum
        s = 0.5*(s+h*sum) #0.5 is because the h is halfed than last time
    return s
def trapzd(func,a,b,s,n):
    """ 
    Array version of trapzd1
    This func is not used for calc a int by trapzd method. This is just used for call several times and add the result of everytime, where the first time gives the two end point values, i.e. 1./2.*(f1+fN)
    follow trapzd of my NR book, P131
    ? don't know why use it, tnm for the same thing...
    """
    #print n
    if n==1:
        s = 0.5*(b-a)*(func(a)+func(b)) #maybe write to array
    else:
        it = 2**(n-2)
        tnm = float(it) #!!!!
        h = (b-a)/tnm #h=del in NR
        xs = np.linspace(a+0.5*h,b-0.5*h,it)
        s = 0.5*(s+h*func(xs).sum()) #0.5 is because the h is halfed than last time
    return s
def simps(func,a,b,limit=20,eps=1.e-5): #perfectly right!
    ost = -np.inf; os = -np.inf #o means old
    st = 0;
    for i in range(limit):
        j = i+1 #
        st = trapzd1(func,a,b,st,j)  # trapzd for array func; trapzd1 for not-array function.
        print('non-array versoin of simps now')
        s = (4.*st-ost)/3.
        if j>5:
            if abs(s-os)/abs(os) < eps:
                return s
            if s==0 and os==0: #may combine this two if in future
                return s
        os = s
        ost = st
    print('warning: two many steps')
    return s


def autoscale_x(ax,margin=0.1):
    """This function rescales the y-axis based on the data that is visible given the current xlim of the axis.
        ax -- a matplotlib axes object
        margin -- the fraction of the total height of the y-data to pad the upper and lower ylims"""
    
    def get_leftmost_rightmost(line):
        xd = line.get_xdata()
        leftmost = xd.min()
        rightmost = xd.max()
        return leftmost,rightmost
    
    lines = ax.get_lines()
    leftmost,rightmost = inf, -inf
    
    for line in lines:
        new_leftmost, new_rightmost = get_leftmost_rightmost(line)
        if new_leftmost < leftmost: leftmost = new_leftmost#*0.5 # for log scale
        if new_rightmost > rightmost: rightmost = new_rightmost#*2   # for log scale
    
    ax.set_xlim(leftmost,rightmost)

def autoscale_y(ax,margin=0.1):
    """This function rescales the y-axis based on the data that is visible given the current xlim of the axis.
        ax -- a matplotlib axes object
        margin -- the fraction of the total height of the y-data to pad the upper and lower ylims"""
    
    import numpy as np
    ax.get_yscale()=='log'
    
    def get_bottom_top(line):
        xd = line.get_xdata()
        yd = array(line.get_ydata()) # array() fixed by BZ
        lo,hi = ax.get_xlim()
        y_displayed = yd[((xd>lo) & (xd<hi))]
        #h = np.max(y_displayed) - np.min(y_displayed)
        #bot = np.min(y_displayed)-margin*h
        #top = np.max(y_displayed)+margin*h  # this may be useful for linear scale.
        bot = np.min(y_displayed)
        top = np.max(y_displayed)
        return bot,top
    
    lines = ax.get_lines()
    bot,top = np.inf, -np.inf
    
    for line in lines:
        new_bot, new_top = get_bottom_top(line)
        if new_bot < bot: bot = new_bot*0.5 # for log scale
        if new_top > top: top = new_top*2   # for log scale
    
    ax.set_ylim(bot,top)


def org_data(Xs, Ys, xscale='log', yscale='log', xs=[], nlogbins=100, nlinbins=1000, fill_value_=-inf):
    'Xs, list of N arrays.'
    'Ys, same.'
    'xs, one array for the x axis data points'
    'ys, list of N arrays'
    'Checked.'
    from scipy import interpolate as intp
    xmin = inf
    xmax = -inf
    for i in range(len(Xs)):
        xmin = min(Xs[i].min(), xmin)
        xmax = max(Xs[i].max(), xmax)
    if xs == []:
        if xscale == 'log':
            xs = ebs( xmin, xmax, int(log10(xmax/xmin))*nlogbins + int(nlogbins/2) )
        if xscale == 'linear':
            xs = linspace(xmin, xmax, nlinbins)
    ys = []
    for i in range(len(Ys)):
        if xscale == 'log' and yscale == 'log':
            #y = exp( intp.interp1d( log(Xs[i]), log(Ys[i]), kind='linear', bounds_error=False, fill_value=-inf)(log(xs)) )
            y = exp( intp.interp1d( log(Xs[i]), log(Ys[i]), kind='linear', bounds_error=False, fill_value=fill_value_)(log(xs)) )
        if xscale == 'linear' and yscale == 'log':
            y = exp( intp.interp1d( Xs[i], log(Ys[i]), kind='linear', bounds_error=False, fill_value=fill_value_)(xs) )
        if xscale == 'linear' and yscale == 'linear':
            y = intp.interp1d( Xs[i], Ys[i], kind='linear', bounds_error=False, fill_value=fill_value_)(xs)
        y[ where(isnan(y)) ] = 0 # only here might cuz problem. But chance is low. A better way is to fix the interpolation.
        ys = ys + [y]
    return xs, ys


def curve2hist(xx, yy, bins, plot_style='EdNdE'):
    binsC = sqrt(bins[1:]*bins[:-1]) # For Emuon1/2
    #ax.plot( xx, yy*0.2*log(10), 'ro-', lw=1.5, ms=3, label=r'DIS $\mu1$' )
    if plot_style=='EdNdE':  
        tot_num = integrate.simps( yy, log(xx) )  # Got the total number
        def tmp_intp(lnEmu_):  # interp the curve
            'Input: ln(Emu_);  Output: EdNdE( ln(Emu_) )'
            tmp_intp1 = intp.interp1d( log(xx), log(yy), kind='linear', bounds_error=False, fill_value=-inf )  # the warning is due to 0 in tmp[1], no problem. 
            return exp(tmp_intp1(lnEmu_)) #* exp(lnEmu_)
    elif plot_style == 'dNdE':
        tot_num = integrate.simps( yy, xx )
        def tmp_intp(Emu_):
            'Copied from the above and modified'
            tmp_intp1 = intp.interp1d( xx, yy, kind='linear', bounds_error=False, fill_value='extrapolate' )  # the warning is due to 0 in tmp[1], no problem. 
            return tmp_intp1(Emu_) #* exp(lnEmu_)
    print('# Tot number from integrating the curve', tot_num)

    hist_E = []; hist = []; 
    for i in range(len(binsC)): # Get the heights of the histogram by integrating the curve over each bin
        hist_E += [ bins[i], bins[i+1] ]
        if plot_style=='EdNdE':
            tmp1 = integrate.quad( tmp_intp, log(bins[i]), log(bins[i+1]), epsabs=0, epsrel=1e-04 )[0]
        else:
            tmp1 = integrate.quad( tmp_intp, bins[i], bins[i+1], epsabs=0, epsrel=1e-04 )[0]
        hist += [ tmp1, tmp1 ]
    tot_num1 = array(hist).sum()/2; 
    print( 'Tot number from the histogram, before renormalization', tot_num1 )
    return hist_E, array(hist)/tot_num1*tot_num

def EdNdE2hist(xx, yy, bins):
    return curve2hist(xx, yy, bins, plot_style='EdNdE')


import astropy.coordinates as coo
def cel2gal(ra, dec, frame_='icrs'):
    'Input in degree; output in degree.'
    'Even if i change deg to rad, the output is still in deg.'
    # obj = coo.SkyCoord(ra,dec,unit='deg',frame='fk5')
    obj = coo.SkyCoord(ra,dec,unit='deg',frame=frame_)
    lon = obj.galactic.l.value
    lat = obj.galactic.b.value
    return lon,lat

def gal2cel(glon,glat):
    coobj = coo.SkyCoord(glon,glat,unit='deg',frame='galactic')
    return coobj.fk5.ra.value, coobj.fk5.dec.value

def generate_rand_1D(pdf, x_min, x_max, y_max, N_simu_):
    'This is for the case of using an analytic PDF; Even if it is not analytic, we can interpolate. So it is universal for 1D random number generation.'
    'Later make it a universal function'
    'Later change the names of the variables below'
    'Later make it more self-adaptive so that it gives me the number of simulated events I want'
    'Checked'
    rand_x = random.rand(N_simu_)*(x_max-x_min) + x_min
    rand_Y = random.rand(N_simu_)*y_max
    rand_y = pdf(rand_x)
    if len(where( rand_y > y_max )[0])>0:
        print('# Error, rand_y > y_max')
        exit()
    idx = where( rand_Y < rand_y  )[0]
    result = rand_x[idx] # later could hisogram it and check.
    return result


def savetxt1(filename, array, **kwargs):
    #print( kwargs )
    #print( type(kwargs) )
    if os.path.exists(filename):
        #raise FileExistsError(f"The file '{filename}' already exists!!!!!!!!!!!!!!!!!!")
        print(f"Warning: the file '{filename}' already exists!!!!!!!!!!!!!!!!!!!!!")
    else:
        np.savetxt(filename, array, **kwargs)

def add_quadrature(a): 
    'a is a list or array'
    return sqrt(sum(array(a)**2))

def rel_diff(x1, x2):
    if x1 != 0:
        return (x2-x1)/x1
    elif x2 != 0: # x1=0 and x2!=0
        return (x1-x2)/x2
    else: # x1=0 and x2=0
        return 0
        


'############################ Healpy related  #############################'
for i0 in range(0):  # Healpy related
    def array2hp(dat,outfile,clobber=0):
        '''
        The number of columns should be the number of the data channel
        '''
        mp = pf.open('/home/beizhou/desktop/data/0useoften/hp_raw/1_0.fits')
        try:
            num_bins = dat.shape[1]
        except:
            num_bins = 1
            dat = dat.reshape(-1,1)
        col = []
        for i in range(num_bins):
            col1 = pf.Column(name='CHANNEL'+str(i+1),format='f8',array=dat[:,i])
            col = col + [col1]
        cols = pf.ColDefs(col)
        tbhdu = pf.new_table(cols)
        mp[1].data = tbhdu.data
        mp.writeto(outfile,clobber=clobber)  #!
    
    def hp_1_2_n(infile):
        d = pf.open(infile)[1].data
        num_chnl = len(d.columns)
        for i in range(num_chnl):
            print(i)
            outfile = infile[0:-5]+'_chnl'+str(i+1)+'.fits'
            print(outfile)
            use.array2hp(d.field(i),outfile)
     
    def ev2hp(thetas_, phis_, Nside_):
        'Events to healpix map'
        'thetas_ in rad, co latitude;  phis_ in rad, longitude.'
        Npix = 12*Nside_**2
    
        nu_idx = hp.ang2pix(Nside_, thetas_, phis_) # idx in healpix array
        binss = array( [-0.5] + list(arange(Npix)+0.5) ) # bins, -0.5, 0.5, 1.5, ...
        counts, xxx = histogram( nu_idx, binss ) # Num of counts for idx = 0,1,2,...
    
        indices = arange(Npix) # This gives all the indices, [0,1,2,3,...]
        m = zeros(hp.nside2npix(Nside_))
        m[indices] = counts
        return m
    
    def view_hp(file, min0=None, max0=None, norm0='linear', cmap0='plasma', cbar0=True):
        m = pf.open(file)[1].data.field('T')
        hp.mollview(m, min=min0, max=max0, norm=norm0, cmap=cmap0, cbar=cbar0)
        plt.savefig('/Users/beizhou/desktop/tmp.pdf')
        plt.show()
    
    def view_hp_cmpr(array):
        'To view multiple hp maps, using the same max and min and scale'
        'In put is an array of multiple arrays of hp maps'
        hp.mollview(m)
        plt.show()
        # To be finished
'########################### !Healpy related ! ############################'





'''
def print_err_10(x,xerr):
    if np.isscalar(x):
        x = np.array([x])
        xerr = np.array([xerr])         
    y = 10**x
    yerr = 10**x*np.log(10)*xerr
    for i in range(y.shape[0]):
        if i != y.shape[0]-1:
            print y[i],'  ',
        else:
            print y[i]
    for i in range(yerr.shape[0]):
        if i != yerr.shape[0]-1:
            print yerr[i],'  ',
        else:
            print yerr[i]

def print_err(x,xerr):
    if np.isscalar(x):
        x = np.array([x])
        xerr = np.array([xerr])         
    y = x #copied from print_err_10
    yerr = xerr
    for i in range(y.shape[0]):
        if i != y.shape[0]-1:
            print y[i],'  ',
        else:
            print y[i]
    for i in range(yerr.shape[0]):
        if i != yerr.shape[0]-1:
            print yerr[i],'  ',
        else:
            print yerr[i]


def map2alm(dat):
    Npix = dat.shape[0]
    Nside = int(sqrt((Npix)/12.))
    theta,phi = hp.pix2ang(Nside,np.arange(Npix))
    from scipy.special import sph_harm as sh
    lmax = 3*Nside-1

    alms = np.arange((lmax+1)*(lmax+2)/2,dtype='complex')
    i = 0
    for m in range(lmax+1): #大的不要循环...
        for l in range(m,lmax+1):
            Ylm = sh(m,l,theta=phi,phi=theta)#it's OK
            alms[i] = 4*pi/Npix*(Ylm*dat).sum()
            i = i+1
    return alms

def alm2mp(alms):
    lmax = int((sqrt(1+8*alms.shape[0])-3.)/2.)
    Nside = int((lmax+1)/3.)
    Npix = Nside**2*12
    indx = np.arange(Npix)
    theta,phi = hp.pix2ang(Nside,np.arange(Npix))
    lms = np.zeros((alms.shape[0],2))
    i = 0
    for l in range(lmax+1): #大的不要循环...
        for m in range(l+1):
            lms[i] = np.array([l,m])
            i = i+1

    dat = np.zeros(Npix,dtype='complex')
    from scipy.special import sph_harm as sh
    for i in range(Npix):
        Ylm = sh(lms[:,1],lms[:,0],theta=phi[i],phi=theta[i])#it's OK
        dat[i] = (Ylm*alms).sum()
    return dat
'''
