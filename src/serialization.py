import pickle
import io

class Serializable:
    def to_bytes(self):
        buffer = io.BytesIO()
        pickle.dump(self, buffer)

        return buffer.getbuffer()

    @staticmethod
    def from_bytes(buffer):
        data = pickle.loads(buffer)
        return data
