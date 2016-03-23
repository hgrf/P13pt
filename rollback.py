# -*- coding: utf-8 -*-
"""
This script can roll back the RFLPA library to a specific git version
in order to keep compatibility of your code with a specific working
revision. It is a bit dangerous, as it physically affects the library
and changes files, so there should always only be one instance of
analysis script that accesses these functions and they should only be
used when necessary (so the rollback functions should by default be
commented). Also be careful not to use these functions for any analysis
script that was written before they were implemented, otherwise you have
to "un-rollback" manually using "git checkout master".

Usage:

    needrollback = False        # False by default
    if needrollback:
        from RFLPA.rollback import rollback, unrollback
        rollback('340aa1904d5f9faaf1f475eb2c541d5553e1d76e') # replace code by working revision (get using "git rev-parse HEAD")
    
    # do your data analysis here
    
    if needrollback:
        unrollback()


@author: Holger Graef
"""

from git import Repo
import os

repo = None

def rollback(revision):
    global repo
    repo = Repo(os.path.dirname(__file__))  # initialise repo
    
    # check everything is the way we expect it to be
    assert not repo.bare
    if repo.is_dirty():
        print "Changes have been made to the repository, please tidy up first"
        quit()
    if repo.rev_parse('HEAD') != repo.rev_parse('master'):
        print "You're currently not in the master branch of RFLPA, please checkout master branch"
        quit()
    
    # and roll back
    print "Current RFLPA revision:", repo.rev_parse('HEAD')
    print "Rolling back to revision:", revision
    repo.git.checkout(revision)
    
def unrollback():
    print "Going back to most recent RFLPA revision."
    repo.git.checkout(repo.heads.master)
    
# some comments:
# would be nicer to create a new folder with a clone
# of the repository and the right version instead of
# changing the "main" copy all the time