import sys
from astropy.io import fits
import numpy as np
import multiprocessing
import re
import os
#from tqdm import tqdm
import time
np.set_printoptions(threshold=np.nan)

def outOfBounds(xcor, ycor, xlen, ylen):
    return (xcor >= xlen or ycor >= ylen or xcor < 0 or ycor < 0)

def getRingArray(data, x, y, outer_rad, inner_rad, xlen, ylen):
    arr = []

    for i in range(2*outer_rad + 1):
        for j in range(outer_rad - inner_rad + 1):
            xcor = x - outer_rad + i
            y1 = y - outer_rad + j
            y2 = y + inner_rad + j
            if not outOfBounds(xcor,y1,xlen,ylen):
                arr.append(data[xcor][y1])
            if not outOfBounds(xcor,y2,xlen,ylen):
                arr.append(data[xcor][y2])

    for i in range(2*inner_rad - 1):
        for j in range(outer_rad - inner_rad + 1):
            ycor = y - inner_rad + 1 + i
            x1 = x - outer_rad + j
            x2 = x + outer_rad -j
            if not outOfBounds(x1,ycor,xlen,ylen):
                arr.append(data[x1][ycor])
            if not outOfBounds(x2,ycor,xlen,ylen):
                arr.append(data[x2][ycor])

    return arr

def getSMA(galname, gallist):
    file = open(gallist, "r")
    split = galname.split("_")
    gal = split[0]
    filt = split[1]
    parsedfil = []
    u_ind = -1
    g_ind = -1
    i_ind = -1
    z_ind = -1
    for line in file:
        parsedfil.append(np.array(re.split("\s+", line)))
    parsedfile = np.array(parsedfil)
    for line in parsedfile:
        if(line[1] == 'Name'):
            for x in range(len(line)):
                if(line[x] == 'u_Re(arcsec)'):
                    u_ind = x
                    g_ind = x+1
                    i_ind = x+3
                    z_ind = x+4
    rad = 0
    for line in parsedfile:
        if(line[1] == gal):
            if(filt == "u"):
                rad = int(float(line[u_ind]))
            elif(filt == "g"):
                rad = int(float(line[g_ind]))
            elif(filt == "i"):
                rad= int(float(line[i_ind]))
            elif(filt == "z"):
                rad = int(float(line[z_ind]))
    rad /= 0.187
    rad *= 5
    file.close()
    return rad

def rmf(filename,galname):
    rad = getSMA("VCC" + galname,"gal_list.cat")
    scilist = fits.open(filename)
    data = scilist[0].data
    xlen = len(data)
    ylen = len(data[0])
    x0 = xlen/2
    y0 = ylen/2
    newdata = np.zeros((xlen,ylen))
    #rad_dist = 8
    #outrad = int(rad/9)
    #inrad = outrad - rad_dist
    #if outrad == inrad or outrad <= 0 or inrad <= 0:
        #outrad = 20
        #inrad = 10
    outrad = 20
    inrad = 10
    #print(outrad,inrad)
    outsidevals = []
    insidevals = []
    for i in range(xlen):
        for j in range(ylen):
            if(i >= x0-rad and i <= x0+rad and j >= y0-rad and j <= y0+rad):
                arr = getRingArray(data, i, j, outrad, inrad, xlen, ylen)
                subt = np.median(arr)
                newdata[i][j] = data[i][j] - subt
                insidevals.append(newdata[i][j])
            else:
                newdata[i][j] = data[i][j]
                outsidevals.append(newdata[i][j])

    median = np.median(outsidevals) - np.median(insidevals)

    for i in range(xlen):
        for j in range(ylen):
            if(i >= x0-rad and i <= x0+rad and j >= y0-rad and j <= y0+rad):
                newdata[i][j] = newdata[i][j] + median
    hdu = fits.PrimaryHDU(newdata)
    newfilename = filename[:-5] + '_mediansub.fits'

    try:
        os.remove(newfilename)
    except OSError:
        pass

    hdu.writeto(newfilename)

def rmf_process(lines_to_run):
    for line in lines_to_run:
        filters = ["u","i","z"]
        for filter in filters:
            filename = "VCC" + line + "_" + filter + ".fits"
            galname = line + "_" + filter
            print("Starting on " + galname)
            try:
                rmf(filename,galname)
            except Exception as e:
                print(e)
                continue
        print("Completed RMF Procedure for VCC" + str(line))


if __name__ == "__main__":
    if(not (len(sys.argv) == 2)):
        print("Usage: python MedianRing.py <tags filename>")
    else:
        #print("Waiting for 90 minutes for download to finish")
        #time.sleep(5400)

        tagsfile = sys.argv[1]
        f = open(tagsfile, "r")
        lines = []
        for line in f.readlines():
            lines.append(line[:-1])
        threads = 4
        splits = int(np.ceil(float(len(lines))/threads))
        linesplits = [lines[i:i + splits] for i in range(0, len(lines), splits)]
        processes = []
        if len(linesplits) < threads:
            threads = len(linesplits)
        for i in range(threads):
            p = multiprocessing.Process(target=rmf_process, args=(linesplits[i],))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()
        print("All RMFs completed!")
