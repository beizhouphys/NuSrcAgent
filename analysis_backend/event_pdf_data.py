"""Shared event-data view for SkyLLH PDF evaluation; no data copy or selection."""


class EventPDFData:
    def __init__(self, events):
        self.events = events

    def __getitem__(self, name):
        return self.events[name]

    def get_data(self, name):
        return self.events[name]
