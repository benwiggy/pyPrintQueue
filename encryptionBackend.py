#!/usr/bin/python
# -*- coding: utf-8 -*-

# ENCRYPTION PDF-to-file Python CUPS Backend v.0.1
# by Ben Byram-Wigfield

# Backend allows for post-processing using MacOS's PDFKit
#  (see the github PDFSuite for PDF manipulation routines.)
# PDFs are saved encrypted with password. 
# Note very useful but good proof of concept.


import os, sys, syslog
import pwd, grp
from Foundation import NSMutableData

from Quartz import PDFDocument, kCGPDFContextAllowsCopying, kCGPDFContextAllowsPrinting, kCGPDFContextUserPassword, kCGPDFContextOwnerPassword
from CoreFoundation import (NSURL)

copyPassword = "12345678" # Password for copying and printing
openPassword = copyPassword # Or enter a different password to open the file.
# Set openPassword as '' to allow opening.

global user

def encrypt(filename, pdfDoc):
	filename =filename.decode('utf-8')
	if not filename:
		print 'Unable to open input file'
		sys.exit(2)
	shortName = os.path.splitext(filename)[0]
	outputfile = shortName+" locked.pdf"
	if pdfDoc :
		options = { 
			kCGPDFContextAllowsCopying: False, 
			kCGPDFContextAllowsPrinting: False, 
			kCGPDFContextOwnerPassword: copyPassword,
			kCGPDFContextUserPassword: openPassword}
		pdfDoc.writeToFile_withOptions_(outputfile, options)
		fixPerms(outputfile)
	return


def logger(msg, logfile):
	# Writes to a log file, stdout, and/or system.log, as required.

	if logfile:
		fileRef = open(logfile, "a")
		fileRef.write(msg)
		fileRef.close
	else:
		sys.stdout.write(msg)
		syslog.syslog(syslog.LOG_ERR, "CUPS PDF backend: %s" % msg)

def getDestination():
	"""Returns the destination path.	
	The Device URI of the printer is: {backend_name}:{/path/to/folder}
	This is a CUPS Environmental variable.
	"""
	#deviceURI = os.environ['DEVICE_URI']
	deviceURI = "mybackend:/Users/Shared/Print"
	write_dir = deviceURI.split(":")[1].strip()
	if os.path.exists(write_dir):
		if os.access(write_dir, os.R_OK | os.W_OK):
			return write_dir
		else:
			logger("User does not have read/write access to: %s" % write_dir, None)
			sys.stdout.flush()
			sys.exit(0)
	else:
		logger("Device URI: Path does not exist: %s\n" % write_dir, None)
		sys.stdout.flush()
		sys.exit(0)

def getType(fileType):
		if fileType == "%PDF":
			extension = ".pdf"
		elif fileType == "%!PS":
			extension = ".ps"
		else:
			extension = ''
		return extension
		
def fixPerms(filename):
	uid = pwd.getpwnam(user).pw_uid
	os.chown(filename, uid, -1)
	os.chmod(filename, 0644)
	return
	

def main(incoming_args):
	backendName = os.path.basename(incoming_args[0])
	destination = getDestination()
	logFile = os.path.join(destination, backendName) + ".log"
	if len(incoming_args) == 1:
		logger("direct %s \"Unknown\" \"Save to PDF\"\n" % backendName, None)
		sys.stdout.flush()
		sys.exit(0)
	if len(incoming_args) not in (6,7):
		sys.stdout.flush()
		logger("Wrong number of arguments. Usage: %s job-id user title copies options [file]\n" % backendName, None)
		sys.exit(1)

	global user
	jobID, user, title, copies, options = (incoming_args[1:6])
	outFilename = os.path.join(destination, title)
	outFilename = os.path.splitext(outFilename)[0]
	logger(jobID+"\n", logFile)
	logger(user+"\n", logFile)
	logger(title+"\n", logFile)
	logger(copies+"\n", logFile)
	logger(options+"\n", logFile)

# If 5 arguments, take PDF/PS file from stdin; if 6, take filename.
	if 	len(incoming_args) == 7:		
		inFilename = incoming_args[6]
		fileRef = open(inFilename, 'r')
		fileType = fileRef.read(4)
		outFilename += getType(fileType)
		pdfURL = NSURL.fileURLWithPath_(inFilename)
		pdfDoc = PDFDocument.alloc().initWithURL_(pdfURL)
		encrypt(inFilename, pdfDoc)			
		os.rename(inFilename, outFilename)

	else:
		fileType = sys.stdin.read(4)
		outFilename += getType(fileType)
		
		global myDataObject
		myDataObject = NSMutableData.alloc().initWithLength_(0)
		myDataObject.appendBytes_length_(fileType, len(fileType))
		
		for myChunk in sys.stdin:
			myDataObject.appendBytes_length_(myChunk, len(myChunk))
	
		pdfDoc = PDFDocument.alloc().initWithData_(myDataObject)
		encrypt(outFilename, pdfDoc)
	
		fileRef = open(outFilename, "w")
		fileRef.write(myDataObject.getBytes_length_(None, myDataObject.length()))	
		fileRef.close
		
# Fix file permissions of PDF for user
	fixPerms(outFilename)

	
# Make sure everyone can read log.
	os.chmod(logFile, 0744)


if __name__ == "__main__":
    main(sys.argv)