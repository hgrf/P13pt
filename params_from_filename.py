from datetime import datetime
import os


def params_from_filename(filename):
    params = dict()
    # read parameters from file name
    toks = os.path.splitext(os.path.basename(filename))[0].split('_')
    # check if first 2 tokens are time stamp
    first_tok = 0
    if len(toks) >= 2:
        # check if first 2 tokens are time stamp
        try:
            params['timestamp'] = datetime.strptime(toks[0]+'_'+toks[1],"%Y-%m-%d_%Hh%Mm%Ss")
            first_tok = 2
        except ValueError:
            pass
    # iterate through the rest of tokens to read the parameters
    for tok in toks[first_tok:]:
         subtoks = tok.split('=', 1)
         if len(subtoks) > 1:
             params[subtoks[0]] = subtoks[1]
         else:
             params[subtoks[0]] = None
    return params