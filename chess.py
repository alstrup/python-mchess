import serial
import serial.tools.list_ports
import time


class MillenniumChess:
    def __init__(self, port="", mode="USB", verbose=False):
        self.replies = {'v': 7, 's': 67, 'l': 3, 'x': 3, 'w': 7, 'r': 7}
        self.figrep = {"int": [1, 2, 3, 4, 5, 6, 0, -1, -2, -3, -4, -5, -6],
                       "unic": "♟♞♝♜♛♚ ♙♘♗♖♕♔",
                       "ascii": "PNBRQK.pnbrqk"}
        self.mode = mode
        self.verbose = verbose
        if port == "":
            ports = self.port_search()
            if len(ports) > 0:
                print("Found {} Millennium boards.".format(len(ports)))
                port = ports[0]
                print("Autodetected Millennium board at: {}".format(port))
        if port and port != "":
            if self.port_check(port):
                try:
                    self.ser_port = serial.Serial(port, 38400)  # , timeout=1)
                    if self.mode == 'USB':
                        self.ser_port.dtr = 0
                    self.init = True
                    self.port = port
                except (OSError, serial.SerialException) as e:
                    print("Can't open port {}, {}".format(port, e))
                    self.init = False
            else:
                print("Invalid port {}".format(port))
                self.init = False
        else:
            print("No port found.")
            self.init = False

    def version_quick_check(self, port):
        try:
            if self.verbose is True:
                print("Testing port: {}".format(port))
            self.ser_port = serial.Serial(port, 38400)  # , timeout=1)
            if self.mode == 'USB':
                self.ser_port.dtr = 0
            self.init = True
            self.write("V")
            version = self.read(7)
            if len(version) != 7:
                self.ser_port.close()
                self.init = False
                if self.verbose is True:
                    print("Message length {} instead of 7".format(len(version)))
                return None
            if version[0] != 'v':
                if self.verbose is True:
                    print("Unexpected reply {}".format(version))
                self.ser_port.close()
                self.init = False
                return None
            version = '{}.{}'.format(version[1:2], version[3:4])
            if self.verbose is True:
                print("Millenium {} at {}", version, port)
            self.ser_port.close()
            self.init = False
            return version
        except (OSError, serial.SerialException):
            pass
        self.ser_port.close()
        self.init = False
        return None

    def port_check(self, port):
        try:
            s = serial.Serial(port, 38400)  # , timeout=1)
            s.close()
            return True
        except (OSError, serial.SerialException) as e:
            if self.verbose:
                print("Can't open port {}, {}".format(port, e))
            return False

    def port_search(self):
        ports = list(
            [port.device for port in serial.tools.list_ports.comports(True)])
        vports = []
        for port in ports:
            if self.port_check(port):
                version = self.version_quick_check(port)
                if version != None:
                    if self.verbose:
                        print("Found: {}".format(version))
                    vports.append(port)
        return vports

    def add_odd_par(self, b):
        byte = ord(b) & 127
        par = 1
        for _ in range(7):
            bit = byte & 1
            byte = byte >> 1
            par = par ^ bit
        if par == 1:
            # byte = ord(b) & 127
            byte = ord(b) | 128
        else:
            byte = ord(b) & 127
        return byte

    def hexd(self, digit):
        if digit < 10:
            return chr(ord('0')+digit)
        else:
            return chr(ord('A')-10+digit)

    def hex(self, num):
        d1 = num//16
        d2 = num % 16
        s = self.hexd(d1)+self.hexd(d2)
        return s

    def write(self, msg):
        if self.init:
            try:
                self.ser_port.reset_input_buffer()
            except (Exception) as e:
                if self.verbose:
                    print("Failed to empty read-buffer: {}", e)
            gpar = 0
            for b in msg:
                gpar = gpar ^ ord(b)
            msg = msg+self.hex(gpar)
            bts = []
            for c in msg:
                bo = self.add_odd_par(c)
                bts.append(bo)
            try:
                n = self.ser_port.write(bts)
                self.ser_port.flush()
                if self.verbose:
                    print("Written: {}".format(n))
            except (Exception) as e:
                if self.verbose:
                    print("Failed to write {}: {}", msg, e)
        else:
            if self.verbose:
                print("No open port for write")

    def read(self, num):
        rep = []
        if self.init:
            for _ in range(num):
                try:
                    b = chr(ord(self.ser_port.read()) & 127)
                    rep.append(b)
                except (Exception) as e:
                    if self.verbose:
                        print("Read error {}".format(e))
                    pass
        else:
            if self.verbose:
                print("No open port for read")
        if len(rep) > 2:
            gpar = 0
            for b in rep[:-2]:
                gpar = gpar ^ ord(b)
            if rep[-2]+rep[-1] != self.hex(gpar):
                if self.verbose:
                    print("CRC error rep={} CRCs: {}!={}".format(rep,
                                                                 rep[-2], self.hex(gpar)))
                return []
        return rep

    def get_version(self):
        version = ""
        self.write("V")
        version = self.read(7)
        if len(version) != 7:
            return ""
        if version[0] != 'v':
            return ""
        version = '{}.{}'.format(version[1]+version[2], version[3]+version[4])
        return version

    def get_board_position_raw(self):
        cmd = "S"
        self.write(cmd)
        rph = self.read(67)
        if len(rph) != 67:
            return ""
        if rph[0] != 's':
            return ""
        return rph[1:65]

    def get_board_position(self):
        rp = self.get_board_position_raw()
        position = [[0 for x in range(8)] for y in range(8)]
        if len(rp) == 64:
            for y in range(8):
                for x in range(8):
                    c = rp[7-x+y*8]
                    i = self.figrep['ascii'].find(c)
                    if i == -1:
                        print("Invalid char in raw position: {}".format(c))
                        return None
                    else:
                        f = self.figrep['int'][i]
                        position[y][x] = f
        else:
            print("Error in board postion, received {}".format(len(board_raw)))
            return None
        return position

    def print_position_ascii(self, position):
        print("  +------------------------+")
        for y in range(8):
            print("{} | ".format(8-y))
            for x in range(8):
                f = position[7-y][x]
                c = '?'
                for i in range(len(self.figrep['int'])):
                    if self.figrep['int'][i] == f:
                        c = self.figrep['unic'][i]
                        break
                print(" {} ".format(c), end='')
            print("|")
        print("  +------------------------+")
        print("    A  B  C  D  E  F  G  H")

    def disconnect(self):
        if self.init:
            self.ser_port.close()
            self.init = False


if __name__ == '__main__':
    board = MillenniumChess(verbose=False)

    '''
        cmd = "L50"
        for _ in range(81):
            cmd = cmd + "C4"
        board.write(cmd)
        # board.write("V")
        # time.sleep(0.1)
        board.read(3)
        # board.write("S")
        # board.read(10)

        time.sleep(5)
        cmd = "X"
        board.write(cmd)
        board.read(3)
    '''
    if board.init:
        version = board.get_version()
        print("Millenium board version {} at {}".format(version, board.port))

        board_raw = board.get_board_raw()
        board.print_ascii_board(board_raw)
        if len(board_raw) == 64:
            for y in range(8):
                for x in range(8):
                    print(board_raw[7-x+(7-y)*8], end="")
                print()
        else:
            print("Received {}".format(len(board_raw)))

        board.disconnect()
    else:
        print("No board.")
    print("closed.")
