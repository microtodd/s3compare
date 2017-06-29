#!/usr/bin/python
#
import tempfile
import subprocess
import sys
import os
import shutil
import filecmp
import getopt
import difflib

def printHelp():
    print '''    s3compare

    Required:
    -l <dir>        Local dir to compare to.

    Optional:
    -b <bucketName> Name of bucket...defaults to "default"
    -f <folder>     Name of folder in bucket. Example: "folder1" checks s3://bucket/folder1
                    If not specified, will compare entire bucket
    -o <outdir>     Name of dir to save outputs (files in bucket that are not local, and patch-like diffs)
                    If not specified, nothing is saved
    -p <profile>    Name of aws profile to use. Defaults to "default"
    -h              print help and exit

    Assumes aws cli installed and creds configured as a profile.
    '''

def syncS3ToLocal(bucketName=None,path=None,profile=None):

    # Create temp dir
    tempDir = tempfile.mkdtemp()

    # S3 sync
    subprocess.call(['aws','s3','sync','s3://'+bucketName+'/'+path,tempDir,'--profile',profile])

    # return dir
    return tempDir

def compare(bucketDir=None,localDir=None):
    comp = filecmp.dircmp(bucketDir,localDir)
    comp.report()

    # Recursion, dude.  https://docs.python.org/2/library/filecmp.html
    return comp

def saveCompare(comp=None,outDir=None,tempDir=None,localDir=None):
    if not os.path.isdir(outDir):
        os.makedirs(outDir)
    for myFile in comp.diff_files:
        # Skip dirs
        if os.path.isdir(tempDir + '/' + myFile):
            continue
        print 'diff=> ' + myFile + ' (diff saved to ' + outDir + '/diff_' + myFile + ')'
        outputFile = open(outDir + '/diff_' + myFile, 'w+')
        for line in difflib.context_diff(open(tempDir + '/' + myFile).readlines(),open(localDir + '/' + myFile).readlines(),fromfile='s3',tofile='local'):
            outputFile.write(line)
        outputFile.close()
    for myFile in comp.left_only:
        # Skip dirs
        if os.path.isdir(tempDir + '/' + myFile):
            continue
        print 'In s3 but not local=> ' + myFile + ' (saved to ' + outDir + ')'
        shutil.copyfile(tempDir + '/' + myFile,outDir + '/' + myFile)

def main(argv):

    # Args
    bucket = 'default'
    bucketFolder = None
    localDir = None
    outDir = None
    profile = 'default'
    opts, args = getopt.getopt(argv,'hf:b:l:o:p:')
    for opt, arg in opts:
        if opt == '-h':
            printHelp()
            sys.exit(0)
        if opt == '-f':
            bucketFolder = str(arg)
        if opt == '-b':
            bucket = str(arg)
        if opt == '-l':
            localDir = str(arg)
        if opt == '-o':
            outDir = str(arg)
        if opt == '-p':
            Profile = str(arg)

    if localDir is None:
        print 'Error: must specify localdir with -l'
        sys.exit(1)
    if bucketFolder is None:
        bucketFolder = ''

    # user validate
    if outDir is None:
        print 'Comparing s3://' + str(bucket) + '/' + bucketFolder + ' to ' + localDir + ' using profile ' + str(profile)
    else:
        print 'Comparing s3://' + str(bucket) + '/' + bucketFolder + ' to ' + localDir + ' and saving results to ' + str(outDir) + ' using profile ' + str(profile)
    userInput = raw_input('Continue? (y/n): ')
    if userInput != 'y' and userInput != 'Y':
        print 'Aborting.'
        return

    # grab bucket
    tempDir = syncS3ToLocal(bucketName=bucket,path=bucketFolder,profile=profile)

    # diff
    comp = compare(bucketDir=tempDir,localDir=sys.argv[2])

    # Save output
    if outDir is not None:
        saveCompare(comp=comp,outDir=outDir,tempDir=tempDir,localDir=localDir)
        
    # Cleanup
    if tempDir.count('/') > 1:
        shutil.rmtree(tempDir)

###
if __name__ == '__main__':
    main(sys.argv[1:])

