class Session:
    def __init__(self, title, date, startTime, endTime, message, overview, emotion, keypoints):
        self.title = title
        self.date = date
        self.startTime = startTime
        self.endTime = endTime
        self.message = message
        self.overview = overview
        self.emotion = emotion
        self.keypoints = keypoints