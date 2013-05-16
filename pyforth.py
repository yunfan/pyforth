#!/usr/bin/env python
# -*- utf-8 -*-

import sys
import time
import itertools
import pprint
import traceback

delay = lambda sec=0.001: time.sleep(sec)


    ## stats for jumping
STAT_ABORT, STAT_COMPILER, STAT_EXECUTER, STAT_TIBOUT, STAT_EXIT = range(5)
names = ['STAT_ABORT', 'STAT_COMPILER', 'STAT_EXECUTER', 'STAT_TIBOUT', 'STAT_EXIT']

## concepts for forth
STACK = []                              ## the statck
RSTACK = []                             ## the return stack
CODES = []                              ## the code segment, its the dictionary concept,
                                        ## i dont use that name which could cause conflict with python's dict
CACHE = {}                              ## cache for quickly find the word's location, the structure
                                        ## { word_name: [xt_idx, immediatable], ... }
                                        ## cant support forth WORD like MARKER directly

REG = {
    'STAT': STAT_TIBOUT,
    'TIB': '',
    'TIB_IDX': 0,
    'IP': -1,
    'COMPILING': False,
    'LAST_WORD': None,
    'LAST_NAME': None,
    'DEBUG': False,
}

def debug_calldump(func):
    orig = func
    def proxy(*args, **kargs):
        ret = orig(*args, **kargs)
        if REG['DEBUG']:
            print "Call %s with args: %s, %s, return %s" % (orig.func_name, repr(args), repr(kargs), repr(ret))
            print ''
        return ret
    return proxy

## utils functions which would have a 'inter_' prefix
def debug_inter(func):
    orig = func
    def proxy(*args, **kargs):
        if REG['DEBUG']: print 'BEFORE: %s with %s %s' % (orig.func_name, repr(args), repr(kargs))
        if REG['DEBUG']: pprint.pprint((REG, RSTACK), indent=1)
        res = orig(*args, **kargs)
        if REG['DEBUG']: print 'AFTER: %s' % orig.func_name
        if REG['DEBUG']: pprint.pprint((REG, RSTACK), indent=1)
        if REG['DEBUG']: print ''
        return res
    return proxy

@debug_inter
def inter_nextstring(delim):
    str_end = REG['TIB'].find(delim, REG['TIB_IDX'])

    if str_end != -1:
        ## we got a string
        s = REG['TIB'][REG['TIB_IDX']:str_end]
    else:
        ## we got the last string
        s = REG['TIB'][REG['TIB_IDX']:]
        REG['STAT'] = STAT_TIBOUT

    REG['TIB_IDX'] += (len(s) + len(delim))

    return s

#@debug_inter
def inter_nexttoken():
    while True:
        token = inter_nextstring(' ')
        if token:
            return token.lower()
        elif REG['STAT'] == STAT_TIBOUT:
            return      ## here we met the end of TIB. no token got
        delay()

@debug_calldump
def inter_findref(s):
    return CACHE.get(s, (None, False))

@debug_inter
def code_colon():
    newname = inter_nexttoken()
    if not newname:
        REG['STAT'] = STAT_EXIT
        return

    REG.update({
        'LAST_WORD': len(CODES),
        'LAST_NAME': newname,
        'COMPILING': True,
        'STAT': STAT_COMPILER,
        'IP': RSTACK.pop(),
    })

## primetive functions which would have a 'code_' prefix
@debug_inter
def code_code():
    pycode = inter_nextstring('END-CODE')
    code = compile(pycode, __file__, 'exec', 0)
    ## fuck python
    ##globl = dict()
    ##globl.update(globals())
    ##globl.update({
    ##    'STACK': STACK,
    ##    'RSTACK': RSTACK,
    ##    'REG': REG,
    ##    'CODES': CODES,
    ##    'CACHE': CACHE,
    ##})
    CODES.append(lambda : eval(code))
    CACHE[REG['LAST_NAME']] = [REG['LAST_WORD'], False]      ## True is the default flag, which could be changed later by ;
    REG.update({
        'TIB_IDX': REG['TIB_IDX'] - len('END-CODE'),
        'STAT': STAT_ABORT,
        'IP': RSTACK.pop(),
        'COMPILING': False,
    })
    return

@debug_inter
def code_endcode():
    ip = RSTACK.pop()
    REG.update({
        ##'COMPILING': False,
        'IP': ip,
    })
    return


## stat processing functions which would have a 'do_' prefix
@debug_inter
def do_abort():
    filter(None, (RSTACK.pop() for idx in xrange(len(RSTACK)))) ## do clean the RSTACK while keep the reference
    REG['IP'] = -1
    ## i hate python and my model
    token = inter_nexttoken()
    if token is None:
        REG['STAT'] = STAT_TIBOUT
        return

    ref, immediatable = inter_findref(token)
    if ref is None:
        REG['STAT'] = STAT_EXIT
        return

    RSTACK.append(REG['IP'])           ## this would cause executer return to STAT_ABORT
    REG['IP'] = ref
    REG['STAT'] = STAT_EXECUTER

@debug_calldump
def do_compiler():
    token = inter_nexttoken()
    if token is None:
        REG['STAT'] = STAT_TIBOUT
        return

    ref, immediatable = inter_findref(token)
    if ref is None:
        REG['STAT'] = STAT_EXIT
        return

    if immediatable:
        RSTACK.append(REG['IP'])
        REG['IP'] = ref
        REG['STAT'] = STAT_EXECUTER
        return

    CODES.append(ref)

@debug_inter
def do_executer():
    #try:
    #    xt = CODES[REG['IP']]
    #except:
    #    pprint.pprint(REG, indent=2)
    #    REG['STAT'] = STAT_EXIT
    #    return
    xt = CODES[REG['IP']]
    if callable(xt):
        xt()
        if REG['COMPILING']:
            REG['STAT'] = STAT_COMPILER
        elif REG['IP'] == -1:
            REG['STAT'] = STAT_ABORT
        else:
            REG['IP'] += 1
    else:
        RSTACK.append(REG['IP'])
        REG['IP'] = xt

@debug_calldump
def do_tibout():
    try:
        REG['TIB'] = REG['STDIN'].next()
        REG['TIB_IDX'] = 0
        REG['STAT'] = STAT_COMPILER if REG['COMPILING'] else STAT_ABORT
    except KeyboardInterrupt:
        REG['STAT'] = STAT_EXIT
    except EOFError:
        REG['STAT'] = STAT_EXIT

def boot(preload):
    ## buildin CODE initial
    REG['STDIN'] = itertools.chain((l.strip() for l in preload.xreadlines()), (raw_input('> ') for wont_use in itertools.repeat(0))) ## A HACK TODO add a new stat for preload file
    CODES.extend([
        code_colon,
        code_code,
        code_endcode,
    ])
    CACHE.update({
        ':': [0, False],        ## dont need to be immediate
        'code': [1, True],
        'end-code': [2, True],
    })

## building JUMP TABLE
    JUMPS = {
        STAT_ABORT: do_abort,
        STAT_COMPILER: do_compiler,
        STAT_EXECUTER: do_executer,
        STAT_TIBOUT: do_tibout,
    }
    while 1:
        ## not a good FSM
        stat = REG['STAT']
        if REG['DEBUG']: print "\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++[STAT] %s\n" % names[stat]
        if stat == STAT_EXIT:
            break
        try:
            JUMPS[stat]()
        except:
            traceback.print_exc()
            pprint.pprint([REG, CACHE, CODES, RSTACK], indent=2)
            break
        delay()

if '__main__' == __name__:
    boot(open(sys.argv[1], 'r'))
