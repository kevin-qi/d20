import pendulum

class ABOtime():
    """
    ABO timestamps helper functions - abstract away cumbersome timestamp calculations!!!
    """

    def now(self):
        """
        TODO: Return current timestamp, season day, season number
        """
        return {'timestamp': pendulum.now('UTC')}

    def prev_reset(self):
        """
        TODO: Return timestamp of previous reset (1 minute before reset), season day, season number
        """
        today_reset_time = pendulum.today('UTC').add(hours=22).subtract(minutes=1)
        if(pendulum.now('UTC') > today_reset_time): # If time has already passed reset time for the day, then reset time will be tomorrow
            today_reset_time = today_reset_time.add(hours=24)
        prev_reset_time = today_reset_time.subtract(hours=24) # Previous reset time must be 24 hours before upcoming reset time.
        return {'timestamp': prev_reset_time}

    def prev_prev_reset(self):
        """
        TOOD: Same as prev_reset() but for the day before yesterday
        """
        pass

    def last_season(self):
        """
        TODO: Return timestamp of last season reset (1 min before reset). season day, season number
        """
        pass