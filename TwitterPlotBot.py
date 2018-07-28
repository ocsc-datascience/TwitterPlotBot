#!/usr/bin/env python3
import sys
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
analyzer = SentimentIntensityAnalyzer()
import matplotlib.pyplot as plt
from matplotlib import style
from matplotlib import rcParams
import pandas as pd
import numpy as np
import tweepy
import json
import time
import datetime
import pytz
from config import *
style.use('seaborn-dark')



# Setup Tweepy API Authentication
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth, parser=tweepy.parsers.JSONParser())


# global list keeping track of
# thing's we've already analyzed
analyzed = []
my_name = "BotUSCDataAna"

def CheckForWork(idlast):
    # Search for at most 100 entries since last check;
    # That's a more than reasonable rate limit and we
    # can avoid pagination.
    q = "@BotUSCDataAna Analyze:"
    tweets = api.search(q,since_id=idlast,rpp=100)

    return tweets

def RespondBadRequest(sender,tweet_id):
    msg = f"@{sender} Sorry, I didn't understand your request."
    try:
        api.update_status(msg,in_reply_to_status_id=tweet_id)
    except:
        print(f"Couldn't send this tweet:\n {msg}")

def RespondGeneral(sender,tweet_id,msg,file=None):
    if file is None:
        try:
            api.update_status(msg,in_reply_to_status_id=tweet_id)
        except:
            print(f"Couldn't send this tweet:\n {msg}")
    else:
        try:
            api.update_with_media(file,msg,in_reply_to_status_id=tweet_id)
        except:
            print(f"Couldn't send this tweet:\n {msg}")
    
        
def GetAndAnalyze(target):

    # get the 500 most recent tweets from the target
    all_tweets = []
    fail = False
    for i in range(5):
        try:
            res = api.user_timeline(target,count=100,page=i)
        except tweepy.error.TweepError as e:
            fail = True
            err = "Locked profile: "+target
            return fail,None,err

        all_tweets += res

    # now vader analyze them
    analist = []
    for tweet in all_tweets:
        res = analyzer.polarity_scores(tweet['text'])
        analist.append(res)

    df = pd.DataFrame(analist)

    return fail,df,None

def MakePlot(target,df):

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # reindex
    df = df.reindex(index=df.index[::-1])

    labeltarget = target

    print(len(labeltarget))
    # prepare, then plot, need to do
    # poor man's scaling of font size and
    # figure size for legend to fit
    xright = 0.8
    if len(labeltarget) > 12:
        xright = 0.75
        legfont = 20
    elif len(labeltarget) > 8:
        xright = 0.75
        legfont = 22
    elif len(labeltarget) > 4:
        xright = 0.78
        legfont = 25
    else:
        xright = 0.8
        legfont = 30

    rcParams['xtick.labelsize'] = 25
    rcParams['ytick.labelsize'] = 25
        
    fig = plt.figure(figsize=(18,10))
    fig.subplots_adjust(left=0.095)
    fig.subplots_adjust(bottom=0.1)
    fig.subplots_adjust(top=0.93)
    fig.subplots_adjust(right=xright)

    
    plt.plot(-df.index,df['compound'],marker='o',\
             markersize=8,lw=0.8,label='@'+labeltarget)
    plt.grid()

    leg = plt.legend(loc=(1.01,0.7),fontsize=legfont,\
                     markerscale=2,title='Twitter')
    for line in leg.get_lines():
        line.set_linewidth(4.0)
    plt.setp(leg.get_title(), fontsize=30)

    plt.xlim(-520,20)
    plt.ylim(-1,1)
    plt.xlabel("Tweets Ago",fontsize=25,labelpad=10)
    plt.ylabel("Tweet Polarity",fontsize=25,labelpad=10)
    plt.title(f"Sentiment Analysis of Tweets ({today})",\
              fontsize=28,y=1.01)
    
    pname = "/tmp/"+target+".png"
    plt.savefig(pname)
    
    return pname

def WorkOnTweet(tweet):
    sender = tweet['user']['screen_name']
    tweet_id = tweet['id']
    
    target = ""
    for user in tweet['entities']['user_mentions']:
        if user['screen_name'] != my_name:
            target = user['screen_name']


    if len(target) == 0:
        RespondBadRequest(sender,tweet_id)
        return

    # check if this *user* has previously asked for the same
    # analysis -- we let a different user ask for it though.
    check_ana = [ x for x in analyzed if \
                  x['user'] == sender and \
                  x['target'] == target ]

    if len(check_ana) > 0:
        print(f"Ignoring {target}, because we've already analyzed it")
        return

    fail, df_res, err = GetAndAnalyze(target)

    if fail:
        msg = "@"+sender+" Something went wrong. Error: " + err
        print(msg,tweet_id)
        RespondGeneral(sender,tweet_id,msg)
        return

    plot_path = MakePlot(target,df_res)
    msg = "@"+sender+" Here is your analysis for @"+target+\
          ". Thanks! @"+sender 
    RespondGeneral(sender,tweet_id,msg,file=plot_path)
    # store info so that we don't duplicate tweets
    md = {}
    md['user'] = sender
    md['target'] = target
    analyzed.append(md)
    

# main worker loop
idlast = 0
while True:

    work = CheckForWork(idlast)
    now = datetime.datetime.now(tz=pytz.utc)
    ts = now.strftime("%Y-%m-%d %H:%m:%S")
    print(ts,len(work['statuses']))

    for tweet in work['statuses']:
        WorkOnTweet(tweet)

    if len(work['statuses']) > 0:
        idlast = work['statuses'][-1]['id']


    time.sleep(300)




