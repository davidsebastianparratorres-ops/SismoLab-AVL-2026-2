class Association:
    def __init__(self, replica_id, reference_id):
        self.replica_id = replica_id #B: the event that has the reference
        self.reference_id = reference_id #A: the chosen candidate
