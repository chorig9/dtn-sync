class Communicator:
    def __init__(self, on_receive_callback):
        self.on_receive_callback = on_receive_callback

        on_receive_callback("XXX")

    def send_file(self, file_data):
        pass
                   
