"""Research-only dynamic Poisson attack-defence state-space forecast engine.

A diagonal-covariance assumed-density Extended Kalman Filter (EKF) for Poisson
goals. It is an approximation to a Bayesian Poisson state-space model, NOT an
exact Kalman filter or SportsQuant implementation. No odds used.

State includes individual team log attack and log defence (positive defence
reduces goals conceded), plus shared home/away log scoring baselines. Gaussian
random walk uncertainty accumulates by elapsed days. Each completed match
updates all six local states with a joint two-goal EKF innovation.
"""
import math
from datetime import datetime
from collections import defaultdict
import numpy as np
from scipy.stats import poisson

class DynamicPoissonEKF:
    def __init__(self, home_goal_rate=1.45, away_goal_rate=1.15,
                 initial_team_var=.20, initial_base_var=.035,
                 team_daily_variance=.00035, base_daily_variance=.000005):
        """All hyperparameters are exploratory research choices, not production rules."""
        if home_goal_rate<=0 or away_goal_rate<=0:
            raise ValueError("Positive prior goal rates required")
        self.home_log=math.log(home_goal_rate);self.away_log=math.log(away_goal_rate)
        self.base_var=[float(initial_base_var),float(initial_base_var)]
        self.team={};self.last={}
        self.initial_team_var=float(initial_team_var)
        self.team_daily_variance=float(team_daily_variance)
        self.base_daily_variance=float(base_daily_variance)
        self.base_time=None
        self.updates=0
    def _add(self,team):
        if team not in self.team:
            # attack mean, defense mean, attack variance, defence variance
            self.team[team]=[0.,0.,self.initial_team_var,self.initial_team_var]
            self.last[team]=None
    def _advance(self,team,time):
        self._add(team)
        old=self.last[team]
        if old is not None and time>old:
            days=(time-old).total_seconds()/86400.
            self.team[team][2]+=days*self.team_daily_variance
            self.team[team][3]+=days*self.team_daily_variance
        if old is None or time>old:self.last[team]=time
    def _advance_baseline(self,time):
        old=self.base_time
        if old is not None and time>old:
            days=(time-old).total_seconds()/86400.
            self.base_var=[x+days*self.base_daily_variance for x in self.base_var]
        if old is None or time>old:self.base_time=time
    def _prior(self,home,away,time):
        self._advance(home,time);self._advance(away,time);self._advance_baseline(time)
        h=self.team[home];a=self.team[away]
        # Numerical exponential limits are implementation protections only.
        log_home=max(-7.,min(7.,self.home_log+h[0]-a[1]))
        log_away=max(-7.,min(7.,self.away_log+a[0]-h[1]))
        return math.exp(log_home),math.exp(log_away)
    def predict(self,home,away,time,max_goals=15):
        lh,la=self._prior(home,away,time)
        p1=poisson.pmf(np.arange(max_goals),lh)
        p2=poisson.pmf(np.arange(max_goals),la)
        g=np.outer(p1,p2);g/=g.sum()
        return g,(lh,la)
    def update(self,home,away,home_goals,away_goals,available_at):
        lh,la=self._prior(home,away,available_at)
        ht,at=self.team[home],self.team[away]
        # x=[home attack, away defence, away attack, home defence, mu_home, mu_away]
        x=np.array([ht[0],at[1],at[0],ht[1],self.home_log,self.away_log])
        var=np.array([ht[2],at[3],at[2],ht[3],*self.base_var])
        H=np.array([[lh,-lh,0.,0.,lh,0.],
                    [0.,0.,la,-la,0.,la]],dtype=float)
        R=np.diag([lh,la])
        S=(H*var)@H.T+R
        K=(var[:,None]*H.T)@np.linalg.inv(S)
        innovation=np.array([home_goals-lh,away_goals-la],dtype=float)
        x=x+K@innovation
        # Diagonal assumed-density projection discards cross-covariance.
        var=np.maximum(var*(1.-np.sum(K*H.T,axis=1)),1e-9)
        ht[0],at[1],at[0],ht[1],self.home_log,self.away_log=map(float,x)
        ht[2],at[3],at[2],ht[3],self.base_var[0],self.base_var[1]=map(float,var)
        self.updates+=1
    def snapshot(self):
        return {"teams":len(self.team),"updates":self.updates,
                "home_base_rate":math.exp(max(-7,min(7,self.home_log))),
                "away_base_rate":math.exp(max(-7,min(7,self.away_log))),
                "team_daily_variance":self.team_daily_variance,
                "base_daily_variance":self.base_daily_variance}

    def to_state_dict(self):
        """Portable research checkpoint; exact weights/state, not a production receipt log."""
        return {"version":"research-ekf-v1","home_log":self.home_log,
                "away_log":self.away_log,"base_var":self.base_var,
                "initial_team_var":self.initial_team_var,
                "team_daily_variance":self.team_daily_variance,
                "base_daily_variance":self.base_daily_variance,
                "team":self.team,
                "last":{k:(v.isoformat() if v is not None else None) for k,v in self.last.items()},
                "base_time":self.base_time.isoformat() if self.base_time is not None else None,
                "updates":self.updates}

    @classmethod
    def from_state_dict(cls,state):
        if state.get("version")!="research-ekf-v1":
            raise ValueError("Unknown research checkpoint schema")
        m=cls(initial_team_var=state["initial_team_var"],
              team_daily_variance=state["team_daily_variance"],
              base_daily_variance=state["base_daily_variance"])
        m.home_log=float(state["home_log"]);m.away_log=float(state["away_log"])
        m.base_var=list(map(float,state["base_var"]))
        m.team={str(k):list(map(float,v)) for k,v in state["team"].items()}
        m.last={str(k):(datetime.fromisoformat(v) if v else None) for k,v in state["last"].items()}
        m.base_time=datetime.fromisoformat(state["base_time"]) if state["base_time"] else None
        m.updates=int(state["updates"])
        return m
