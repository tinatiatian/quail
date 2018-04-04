from __future__ import division
from __future__ import print_function
from builtins import zip
from builtins import str
from builtins import range
from sqlalchemy import create_engine, MetaData, Table
import json
import re
import csv
import pandas as pd
import numpy as np
from .egg import Egg, FriedEgg
import dill
import pickle
import os
import deepdish as dd
from .helpers import parse_egg

def load(filepath, update=True):
    """
    Loads eggs, fried eggs ands example data

    Parameters
    ----------
    filepath : str
        Location of file

    update : bool
        If true, updates egg to latest format

    Returns
    ----------
    data : quail.Egg or quail.FriedEgg
        Data loaded from disk

    """

    if filepath == 'automatic' or filepath == 'example':
        fpath = os.path.dirname(os.path.abspath(__file__)) + '/data/automatic.egg'
        return load_egg(fpath)
    elif filepath == 'manual':
        fpath = os.path.dirname(os.path.abspath(__file__)) + '/data/manual.egg'
        return load_egg(fpath, update=False)
    elif filepath.split('.')[-1]=='egg':
        return load_egg(filepath, update=update)
    elif filepath.split('.')[-1]=='fegg':
        return load_fegg(filepath, update=False)
    else:
        raise ValueError('Could not load file.')

def load_fegg(filepath, update=True):
    """
    Loads pickled egg

    Parameters
    ----------
    filepath : str
        Location of pickled egg

    update : bool
        If true, updates egg to latest format

    Returns
    ----------
    egg : Egg data object
        A loaded unpickled egg

    """
    try:
        egg = FriedEgg(**dd.io.load(filepath))
    except ValueError as e:
        print(e)
        # if error, try loading old format
        with open(filepath, 'rb') as f:
            egg = pickle.load(f)

    if update:
        return egg.crack()
    else:
        return egg

def load_egg(filepath, update=True):
    """
    Loads pickled egg

    Parameters
    ----------
    filepath : str
        Location of pickled egg

    update : bool
        If true, updates egg to latest format

    Returns
    ----------
    egg : Egg data object
        A loaded unpickled egg

    """
    try:
        egg = Egg(**dd.io.load(filepath))
    except:
        # if error, try loading old format
        with open(filepath, 'rb') as f:
            egg = pickle.load(f)

    if update:
        return egg.crack()
    else:
        return egg

def loadEL(dbpath=None, recpath=None, remove_subs=None, wordpool=None, groupby=None, experiments=None,
    filters=None):
    '''
    Function that loads sql files generated by autoFR Experiment
    '''

    assert (dbpath is not None), "You must specify a db file or files."
    assert (recpath is not None), "You must specify a recall folder."
    assert (wordpool is not None), "You must specify a wordpool file."
    assert (experiments is not None), "You must specify a list of experiments"

    ############################################################################
    # subfunctions #############################################################

    def db2df(db, filter_func=None):
        '''
        Loads db file and converts to dataframe
        '''
        db_url = "sqlite:///" + db
        table_name = 'turkdemo'
        data_column_name = 'datastring'

        # boilerplace sqlalchemy setup
        engine = create_engine(db_url)
        metadata = MetaData()
        metadata.bind = engine
        table = Table(table_name, metadata, autoload=True)

        # make a query and loop through
        s = table.select()
        rows = s.execute()

        data = []
        for row in rows:
            data.append(row[data_column_name])

        # parse each participant's datastring as json object
        # and take the 'data' sub-object
        data = [json.loads(part)['data'] for part in data if part is not None]

        # remove duplicate subject data for debugXG82XV:debug7XPXQA
        # data[110] = data[110][348:]

        # insert uniqueid field into trialdata in case it wasn't added
        # in experiment:
        for part in data:
            for record in part:
        #         print(record)
                if type(record['trialdata']) is list:

                    record['trialdata'] = {record['trialdata'][0]:record['trialdata'][1]}
                record['trialdata']['uniqueid'] = record['uniqueid']

        # flatten nested list so we just have a list of the trialdata recorded
        # each time psiturk.recordTrialData(trialdata) was called.
        def isNotNumber(s):
            try:
                float(s)
                return False
            except ValueError:
                return True

        data = [record['trialdata'] for part in data for record in part]

        # filter out fields that we dont want using isNotNumber function
        filtered_data = [{k:v for (k,v) in list(part.items()) if isNotNumber(k)} for part in data]

        # Put all subjects' trial data into a dataframe object from the
        # 'pandas' python library: one option among many for analysis
        data_frame = pd.DataFrame(filtered_data)

        data_column_name = 'codeversion'

        # boilerplace sqlalchemy setup
        engine = create_engine(db_url)
        metadata = MetaData()
        metadata.bind = engine
        table = Table(table_name, metadata, autoload=True)

        # make a query and loop through
        s = table.select()
        rows = s.execute()

        versions = []
        version_dict = {}
        for row in rows:
            version_dict[row[0]]=row[data_column_name]

        version_col = []
        for idx,sub in enumerate(data_frame['uniqueid'].unique()):
            for i in range(sum(data_frame['uniqueid']==sub)):
                version_col.append(version_dict[sub])
        data_frame['exp_version']=version_col

        if filter_func:
            for idx,filt in enumerate(filter_func):
                data_frame = filt(data_frame)
        return data_frame

    # custom filter to clean db file
    def experimenter_filter(data_frame):
        data=[]
        indexes=[]
        for line in data_frame.iterrows():
            try:
                if json.loads(line[1]['responses'])['Q1'].lower() in ['kirsten','allison','marisol','marisiol', 'maddy','campbell', 'campbell field', 'kirsten\\nkirsten', 'emily', 'bryan', 'armando', 'armando ortiz', 'maddy/lucy',
                                                                      'paxton', 'lucy']:
                    delete = False
                else:
                    delete = True
            except:
                pass

            if delete:
                indexes.append(line[0])

        return data_frame.drop(indexes)

    def adaptive_filter(data_frame):
        data=[]
        indexes=[]
        subjcb={}
        for line in data_frame.iterrows():
            try:
                if 'Q2' in json.loads(line[1]['responses']):
                    delete = False
                else:
                    delete = False
            except:
                pass

            if delete:
                indexes.append(line[0])
        return data_frame.drop(indexes)

    def experiments_filter(data_frame):
        indexes=[]
        for line in data_frame.iterrows():
            try:
                if line[1]['exp_version'] in experiments:
                    delete = False
                else:
                    delete = True
            except:
                pass

            if delete:
                indexes.append(line[0])
        return data_frame.drop(indexes)


    # this function takes the data frame and returns subject specific data based on the subid variable
    def filterData(data_frame,subid):
        filtered_stim_data = data_frame[data_frame['stimulus'].notnull() & data_frame['listNumber'].notnull()]
        filtered_stim_data = filtered_stim_data[filtered_stim_data['trial_type']=='single-stim']
        filtered_stim_data =  filtered_stim_data[filtered_stim_data['uniqueid']==subid]
        return filtered_stim_data

    def createStimDict(data):
        stimDict = []
        for index, row in data.iterrows():
            try:
                stimDict.append({
                        'text': str(re.findall('>(.+)<',row['stimulus'])[0]),
                        'color' : { 'r' : int(re.findall('rgb\((.+)\)',row['stimulus'])[0].split(',')[0]),
                                   'g' : int(re.findall('rgb\((.+)\)',row['stimulus'])[0].split(',')[1]),
                                   'b' : int(re.findall('rgb\((.+)\)',row['stimulus'])[0].split(',')[2])
                                   },
                        'location' : {
                            'top': float(re.findall('top:(.+)\%;', row['stimulus'])[0]),
                            'left' : float(re.findall('left:(.+)\%', row['stimulus'])[0])
                            },
                        'category' : wordpool['CATEGORY'].iloc[list(wordpool['WORD'].values).index(str(re.findall('>(.+)<',row['stimulus'])[0]))],
                        'size' : wordpool['SIZE'].iloc[list(wordpool['WORD'].values).index(str(re.findall('>(.+)<',row['stimulus'])[0]))],
                        'wordLength' : len(str(re.findall('>(.+)<',row['stimulus'])[0])),
                        'firstLetter' : str(re.findall('>(.+)<',row['stimulus'])[0])[0],
                        'listnum' : row['listNumber']
                    })
            except:
                stimDict.append({
                        'text': str(re.findall('>(.+)<',row['stimulus'])[0]),
                        'color' : { 'r' : 0,
                                   'g' : 0,
                                   'b' : 0
                                   },
                        'location' : {
                            'top': 50,
                            'left' : 50
                            },
                        'category' : wordpool['CATEGORY'].iloc[list(wordpool['WORD'].values).index(str(re.findall('>(.+)<',row['stimulus'])[0]))],
                        'size' : wordpool['SIZE'].iloc[list(wordpool['WORD'].values).index(str(re.findall('>(.+)<',row['stimulus'])[0]))],
                        'wordLength' : len(str(re.findall('>(.+)<',row['stimulus'])[0])),
                        'firstLetter' : str(re.findall('>(.+)<',row['stimulus'])[0])[0],
                        'listnum' : row['listNumber']
                    })
        return stimDict

    # this function loads in the recall data into an array of arrays, where each array represents a list of words
    def loadRecallData(subid):
        recalledWords = []
        for i in range(0,16):
            try:
                f = open(recpath + subid + '/' + subid + '-' + str(i) + '.wav.txt', 'rb')
                spamreader = csv.reader(f, delimiter=',', quotechar='|')
            except (IOError, OSError) as e:
                try:
                    f = open(recpath + subid + '-' + str(i) + '.wav.txt', 'rb')
                    spamreader = csv.reader(f, delimiter=',', quotechar='|')
                except (IOError, OSError) as e:
                    print(e)
            try:
                words=[]
                altformat=True
                for row in spamreader:
                    if len(row)>1:
                        recalledWords.append(row)
                        altformat=False
                        break
                    else:
                        try:
                            words.append(row[0])
                        except:
                            pass
                if altformat:
                    recalledWords.append(words)
            except:
                print('couldnt process '+ recpath + subid + '/' + subid + '-' + str(i) + '.wav.txt')
        return recalledWords

    # this function computes accuracy for a series of lists
    def computeListAcc(stimDict,recalledWords):
        accVec = []
        for i in range(0,16):
            stim = [stim['text'] for stim in stimDict if stim['listnum']==i]
            recalled= recalledWords[i]

            acc = 0
            tmpstim = stim[:]
            for word in recalled:
                if word in tmpstim:
                    tmpstim.remove(word)
                    acc+=1
            accVec.append(acc/len(stim))
        return accVec

    def getFeatures(stimDict):
        stimDict_copy = stimDict[:]
        for item in stimDict_copy:
            item['location'] = [item['location']['top'], item['location']['left']]
            item['color'] = [item['color']['r'], item['color']['g'], item['color']['b']]
            item.pop('text', None)
            item.pop('listnum', None)
        stimDict_copy = [stimDict_copy[i:i+16] for i in range(0, len(stimDict_copy), 16)]
        return stimDict_copy

    ############################################################################
    # main program #############################################################

    # if its not a list, make it one
    if type(dbpath) is not list:
        dbpath = [dbpath]

    # read in stimulus library
    wordpool = pd.read_csv(wordpool)

    # add custom filters
    if filters:
        filter_func = [adaptive_filter, experimenter_filter, experiments_filter] + filters
    else:
        filter_func = [adaptive_filter, experimenter_filter, experiments_filter]

    # load in dbs and convert to df, and filter
    dfs = [db2df(db, filter_func=filter_func) for db in dbpath]

    # concatenate the db files
    df = pd.concat(dfs)

    # subjects who have completed the exp
    subids = list(df[df['listNumber']==15]['uniqueid'].unique())

    # remove problematic subjects
    if remove_subs:
        for sub in remove_subs:
            try:
                subids.remove(sub)
            except:
                print('Could not find subject: ' + sub + ', skipping...')

    # set up data structure to load in subjects
    if groupby:
        pres = [[] for i in range(len(groupby['exp_version']))]
        rec = [[] for i in range(len(groupby['exp_version']))]
        features = [[] for i in range(len(groupby['exp_version']))]
        subs = [[] for i in range(len(groupby['exp_version']))]

        # make each groupby item a list
        groupby = [exp if type(exp) is list else [exp] for exp in groupby['exp_version']]

    else:
        pres = [[]]
        rec = [[]]
        features = [[]]
        subs = [[]]

    # for each subject that completed the experiment
    for idx,sub in enumerate(subids):

        # get the subjects data
        filteredStimData = filterData(df,sub)

        if filteredStimData['exp_version'].values[0] in experiments:

            # create stim dict
            stimDict = createStimDict(filteredStimData)

            sub_data = pd.DataFrame(stimDict)
            sub_data['subject']=idx
            sub_data['experiment']=filteredStimData['exp_version'].values[0]
            sub_data = sub_data[['experiment','subject','listnum','text','category','color','location','firstLetter','size','wordLength']]

            # get features from stim dict
            feats = getFeatures(stimDict)

            # load in the recall data
            recalledWords = loadRecallData(sub)

            # get experiment version
            exp_version = filteredStimData['exp_version'].values[0]

            # find the idx of the experiment for this subjects
            if groupby:
                exp_idx = list(np.where([exp_version in item for item in groupby])[0])
            else:
                exp_idx = [0]

            if exp_idx != []:
                pres[exp_idx[0]].append([list(sub_data[sub_data['listnum']==lst]['text'].values) for lst in sub_data['listnum'].unique()])
                rec[exp_idx[0]].append(recalledWords)
                features[exp_idx[0]].append(feats)
                subs[exp_idx[0]].append(sub)

    eggs = [Egg(pres=ipres, rec=irec, features=ifeatures, meta={'ids' : isub}) for ipres,irec,ifeatures,isub in zip(pres, rec, features, subs)]

    if len(eggs)>1:
        return eggs
    else:
        return eggs[0]

def load_example_data(dataset='automatic'):
    """
    Loads example data

    The example data is an egg containing 30 subjects who completed a free
    recall experiment as described here: https://psyarxiv.com/psh48/. The subjects
    studied 8 lists of 16 words each and then performed a free recall test.

    Parameters
    ----------
    dataset : str
        The dataset to load. Can be 'automatic' or 'manual'. The free recall
        audio recordings for the 'automatic' dataset was transcribed by Google
        Cloud Speech and the 'manual' dataset was transcribed by humans.

    Returns
    ----------
    data : quail.Egg
        Example data
    """

    # can only be auto or manual
    assert dataset in ['automatic', 'manual'], "Dataset can only be automatic or manual"

    # open pickled egg
    try:
        with open(os.path.dirname(os.path.abspath(__file__)) + '/data/' + dataset + '.egg', 'rb') as handle:
            egg = pickle.load(handle)
    except:
        f = dd.io.load(os.path.dirname(os.path.abspath(__file__)) + '/data/' + dataset + '.egg')
        egg = Egg(pres=f['pres'], rec=f['rec'], dist_funcs=f['dist_funcs'],
                  subjgroup=f['subjgroup'], subjname=f['subjname'],
                  listgroup=f['listgroup'], listname=f['listname'],
                  date_created=f['date_created'])
    return egg.crack()
