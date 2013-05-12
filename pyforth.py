#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import traceback
from pprint import pprint as pp

STACK = []
RSTACK = []
WORDS = []
CACHE = {}      ## { word_name: [xt_idx, immediatable], ... }

REG = {
        'SP': 0,
        'RSP': 0,
        'TIB': '',
        'TIB_IDX': 0,
        'IP': 0,
        'LAST_WORD': None,
        'LAST_NAME': None,
        }

FLAGS = {'COMPILING': False, 'DEBUG': False}

def FINDWORD(word):
    return CACHE.get(word, (None, False))

def CALL():
    #print 'xt is %d' % REG['IP']
    try:
        xt = WORDS[REG['IP']]
    except:
        print "\n\n"
        pp(WORDS, indent=2)
        pp(REG, indent=2)
        traceback.print_exc()
        sys.exit(2)

    if callable(xt):
        xt()
        DORET()
    else:
        ##if FLAGS['DEBUG']: print 'RSTACK while calling', RSTACK
        RSTACK.append(REG['IP'] - 1)
        REG['IP'] = xt - 1

def NEXTSTRING(delim):
    str_end = REG['TIB'].find(delim, REG['TIB_IDX'])

    if str_end != -1:
        ## we got a string
        s = REG['TIB'][REG['TIB_IDX']:str_end]
        REG['TIB_IDX'] = str_end + 1
    else:
        ## we got the last string
        s = REG['TIB'][REG['TIB_IDX']:]
        REG['TIB_IDX'] = -1

    ##if FLAGS['DEBUG']: print '\n\nnextstring=%s, length=%d'% (s, len(s))
    return s

def NEXTTOKEN():
    while True:
        token = NEXTSTRING(' ')
        if token:
            return token.lower()
        elif REG['TIB_IDX'] == -1:
            return      ## here we met the end of TIB. no token got

def NEXT():
    while REG['TIB_IDX'] != -1:
        token = NEXTTOKEN()
        if FLAGS['DEBUG']: print 'token: ', token
        if not token: continue

        xt_idx, immediatable = FINDWORD(token)
        if xt_idx is None:
            ## just raise ?
            raise Exception('couldnt found the token %s' % token)

        if FLAGS['COMPILING'] and not(immediatable):
            WORDS.append(xt_idx)
        else:
            ## INTERPRET or immediatable when compiling
            REG['IP'] = xt_idx
            ## EXECUTE()  ## the follow code is what EXECUTE does
            while True:
                ##if FLAGS['DEBUG']: print 'before CALL', CACHE, RSTACK, pp(REG, indent=2), FLAGS; pp(WORDS, indent=2)
                CALL()
                ##if FLAGS['DEBUG']: print 'after CALL IP = %d' % REG['IP']
                ##if FLAGS['DEBUG']: print REG, FLAGS
                if FLAGS['DEBUG']: print 'FLAGS', FLAGS
                if REG['IP'] == -1:
                    if FLAGS['DEBUG']: print "[BREAK]IP == -1"
                    break
                if FLAGS['COMPILING']:
                    if FLAGS['DEBUG']: print "[BREAK] COMPILING == True"
                    break
                REG['IP'] += 1

def DORET():
    REG['IP'] = RSTACK.pop() if len(RSTACK) else -1

def DOCOLON():
    newname = NEXTTOKEN()
    if not newname: raise Exception('error on defining new word, you dont give a word name before enter')
    REG['LAST_WORD'] = len(WORDS)
    REG['LAST_NAME'] = newname
    FLAGS['COMPILING'] = True

def DOCODE():
    ##skip = NEXTSTRING(' ')
    pycode = NEXTSTRING('END-CODE')
    REG['TIB_IDX'] -= 1     ## TODO this is a HACK, need to re-implement the whole NEXTSTRING and NEXTTOKEN
    code = compile(pycode, __file__, 'exec', 0)
    WORDS.append(lambda : eval(code))
    CACHE[REG['LAST_NAME']] = [REG['LAST_WORD'], True]      ## True is the default flag, which could be changed later by ;
                                                            ## that's the reason why i use list not tuple for store
    return

def DOENDCODE():
    FLAGS['COMPILING'] = False
    REG['IP'] = RSTACK.pop() if len(RSTACK) else -1

def BOOTUP(cmd):
    WORDS.extend([
        DOCOLON,
        DOCODE,
        DOENDCODE,
    ])
    CACHE.update({
        ':': [0, True],
        'code': [1, True],
        'end-code': [2, True],
    })
    tibs = cmd
    for line in tibs.readlines():
        REG['TIB'] = line[:-1]
        REG['TIB_IDX'] = 0
        NEXT()

    while True:
        REG['TIB'] = raw_input('> ')
        REG['TIB_IDX'] = 0
        try:
            NEXT()
        except:
            traceback.print_exc()
            sys.exit(1)

if '__main__' == __name__:
    BOOTUP(open(sys.argv[1], 'r'))
