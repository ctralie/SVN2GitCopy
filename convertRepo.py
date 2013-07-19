import os
import re

SVNURL = 'https://svn-vm.egr.duke.edu/svn/TralieRepo'
REPODIR = 'TralieRepo'
NRevisions = 165

#Format of logentry  is file is 
#------------------
#rXXX | username | YYYY-MM-DD HH:MM:SS -0400 (Weekday, Day Month Year) | X lines
#Changed Paths:
#	[A/D/M/R] path (copied from path)
#	...
#
#Commit message
#------------------
#See http://svnbook.red-bean.com/en/1.5/svn.ref.svn.c.log.html for more details
def getRevisionInfo(revNum):
	(stdin, stdout, stderr) = os.popen3("svn log -v -r %i %s"%(revNum, SVNURL))
	lines = stdout.readlines()
	lines = lines[1:-1]#First and last line are ------
	datestuff = lines[0].split('|')
	datestuff = datestuff[2].split()
	#Keep date format in ISO
	#https://www.kernel.org/pub/software/scm/git/docs/git-commit.html#_date_formats
	ISODateStr = "%sT%s"%(datestuff[0], datestuff[1])
	commitMessage = lines[-1].rstrip()
	lines = lines[2:-2]
	changedFiles = []
	for line in lines:
		changedType = line.split()[0]
		line = line[5:].rstrip()
		#Check to see if it's been svn copied from another file
		fromOther = None
		m = re.search('(from.*)', line)
		if m:
			fromOther = line[m.start()+5:m.end()-1]
			if fromOther[0] == '/':
				fromother = fromOther[1:]
			line = line[0:m.start()-1]
		changedName = line
		if changedName[0] == '/':
			changedName = changedName[1:]
		changedName = changedName.rstrip()
		changedFiles.append([changedType, changedName])
	return (ISODateStr, changedFiles, commitMessage)

def execSysCmd(command, verbose = False):
	print command
	(stdin, stdout, stderr) = os.popen3(command)
	if verbose:
		for line in stdout.readlines():
			print line
		for line in stderr.readlines():
			print line

if __name__ == '__main__':
	execSysCmd("svn checkout -r 1 %s"%(SVNURL), True)
	execSysCmd('cp .gitignore %s'%REPODIR)
	os.chdir(REPODIR)
	execSysCmd("git init .")
	for rev in range(1, NRevisions+1):
		os.chdir('..')
		execSysCmd("svn checkout -r %i %s"%(rev, SVNURL), True)
		os.chdir(REPODIR)
		(ISODateStr, changedFiles, commitMessage) = getRevisionInfo(rev)
		print "Revision %i: %s"%(rev, commitMessage)
		for change in changedFiles:
			verbose = True
			[changeType, path] = change
			if changeType in ['A', 'M', 'R']:
				execSysCmd("git add \"%s\""%path, verbose)
			elif changeType == 'D':
				execSysCmd("git rm \"%s\""%path, verbose)
			else:
				print "ERROR: Unrecognized change type %s for %s"%(changeType, path)			
		#Both the committer date and author date need to be set
		#since using the --date flag only updates GIT_AUTHOR_DATE
		#This is Kosher since this is a history migration
		#Also using os.environ in python will not change the environmental
		#variables after the script has finished running so the settings
		#should go back to normal after this script is run 
		#http://alexpeattie.com/blog/working-with-dates-in-git/
		os.environ['GIT_AUTHOR_DATE'] = ISODateStr
		os.environ['GIT_COMMITTER_DATE'] = ISODateStr
		execSysCmd("git commit -m \"%s\""%commitMessage, True)
		
