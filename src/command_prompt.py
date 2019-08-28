class CommandPrompt:
    def __init__(self, sync):
        self.sync = sync
        self.run()

    def run(self):
       user_input = input().split()
       command = user_input[0].lower()
       if command == "query":
           filename = user_input[1]
           self.sync.query_neighbours(filename)
       else:
           print("Command not recognized.")
