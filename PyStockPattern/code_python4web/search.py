import os, argparse, json
import numpy as np
from scipy.interpolate import interp1d

def recursiveFileList(path, ext):
    fListFullPath = []
    fListMainName = []
    for (dirPath, dirNames, fileNames) in os.walk(path):
        for f in fileNames:
            thisExt  = f.split('.')[-1]
            thisMain = f.split('.')[0]
            if(thisExt==ext):
                fListFullPath.append(os.path.join(dirPath, f))
                fListMainName.append(thisMain)
    fListFullPath = np.array(fListFullPath)
    fListMainName = np.array(fListMainName)
    sortIdx = np.argsort(fListFullPath)
    fListFullPath = fListFullPath[sortIdx]
    fListMainName = fListMainName[sortIdx]
    return (fListFullPath, fListMainName)

def loadFile(fileName):
    with open(fileName) as fin:
        content = fin.read().splitlines()
    return content[1:501]

parser = argparse.ArgumentParser(description='OAO')
parser.add_argument('qs', help='Query string')
parser.add_argument('dmin', help='LS day min', type=float)
parser.add_argument('dmax', help='LS day max', type=float)
parser.add_argument('dres', help='LS day res', type=float)

args = parser.parse_args()
qs   = args.qs
dMin = args.dmin
dMax = args.dmax
dRes = args.dres
topN = 5
overlapRatio = 0.3
basePath = os.path.dirname(os.path.realpath(__file__))

# Read db
dbDic = {}
filePaths, fileNames = recursiveFileList(basePath+'/data_csv', 'csv')
for i, fp in enumerate(filePaths):
    cnt = loadFile(fp)
    dates  = [c.split(',')[0] for c in cnt]
    closes = np.array([float(c.split(',')[3]) for c in cnt])
    dbDic[fileNames[i]] = (dates, closes)

# Shift to mean zero
qv = np.array(map(float, qs.split('.')))
qv = qv - np.min(qv)
qv = qv / np.max(qv)

# Scaling
oriX = np.linspace(0, 1, qv.shape[0])
f = interp1d(oriX, qv, bounds_error=False, fill_value='extrapolate')
vecDic = {}
for i in np.linspace(dMin, dMax, (dMax-dMin)/dRes+1):
    v = f(np.linspace(0, 1, i))
    v = v - np.mean(v)
    vecDic[int(i)] = v

# Computing
allResult = []
for d in dbDic:
    dates, closes = dbDic[d]
    dbLen = closes.shape[0]
    tempResult = []
    for k in vecDic:
        thisQv  = vecDic[k]
        thisLen = thisQv.shape[0]
        for j in range(dbLen-thisLen):
            tempDic = {}
            thisDbClip = closes[j:(j+thisLen)]
            # Scale and mean shift for DB clip
            thisDbClip = thisDbClip - np.min(thisDbClip)
            thisDbClip = thisDbClip / np.max(thisDbClip) # Will get warning or error if price reamins the same
            thisDbClip = thisDbClip - np.mean(thisDbClip)
            # Compare
            tempDic['dist'] = np.sum( np.abs( thisQv - thisDbClip ) ) / (1.0*thisLen)
            tempDic['dur']  = thisLen
            tempDic['startIdx'] = j
            tempDic['endIdx']   = j + thisLen - 1
            tempDic['name']      = d
            tempDic['startTime'] = dates[j]
            tempResult.append(tempDic)
    # Overlapping removal
    siAll   = np.array([tr['startIdx'] for tr in tempResult])
    eiAll   = np.array([tr['endIdx']   for tr in tempResult])
    distAll = np.array([tr['dist']     for tr in tempResult])
    durAll  = np.array([tr['dur']      for tr in tempResult]) * overlapRatio
    for i in range(topN):
        idx = np.argmin(distAll)
        allResult.append(tempResult[idx])
        rmIdxFront = np.bitwise_and(siAll<=siAll[idx], (eiAll-siAll[idx])>=durAll)
        rmIdxRear  = np.bitwise_and(siAll >siAll[idx], (eiAll[idx]-siAll)>=durAll)
        rmIdx = np.bitwise_or(rmIdxFront, rmIdxRear)
        distAll[rmIdx] = np.inf

# Get real top-N
allResult = np.array(allResult)
retResult = []
topIdxAll = np.argsort([ar['dist'] for ar in allResult])[0:topN]
# Todo: insert price and pattern, json
for ti in topIdxAll:
    si  = allResult[ti]['startIdx']
    dur = allResult[ti]['dur']
    # Price
    allResult[ti]['price'] = dbDic[allResult[ti]['name']][1][si:si+dur].tolist()
    # Pattern
    pattern = vecDic[dur]
    pattern = pattern - np.min(pattern)
    pattern = pattern * (np.max(allResult[ti]['price']) - np.min(allResult[ti]['price'])) + min(allResult[ti]['price'])
    allResult[ti]['pattern'] = pattern.tolist()
    # Append
    retResult.append(allResult[ti])
print json.dumps(retResult)
