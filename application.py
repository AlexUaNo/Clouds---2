# Assignment in Networking and Cloud Computing.
# Implementation of a file transfer application (DRTP/UDP protocol).
'''
The goal is to develop and analyze a Python-based file transfer application that facilitates seamless data exchange between clients and servers using DRTP over UDP. 
The application reads data in chunks of 994 bytes, adds a custom 6-byte DRTP header, and then sends the data over UDP.
Files are read and written in binary mode (rb and wb), and the struct package is used to pack and unpack headers.
Although the capability exists to transfer two source files simultaneously (multithreading), the application will be limited to permitting only one transfer at a time.

For Client side:
A client reads a file from the computer and sends it over DRTP/UDP, with the file name, server address, and port number provided as command line arguments. 
To implement reliability on top of UDP, the application uses acknowledgments and retransmission logic with a a default value 500ms timeout, employing socket.settimeout(). 

For Server side:
A file transfer server accepts a file from a client via its UDP socket and saves it to the file system. 
Additionally, the server monitors the amount of data received from connected clients, computing and displaying the throughput based on the received data and the connection duration. 
The server's port number must match that used by the client. Upon receiving the file on the server side, it will be opened in binary mode for writing.
'''

import socket                       # For socket programming.
import argparse                     # For parsing command line arguments.
import os                           # For file operations.
import time                         # For time-related functions.
import math                         # For mathematical operations.
from struct import *                # For packing and unpacking data.
import threading                    # For implementing multithreading.
from datetime import datetime       # For working with dates and times.


DEFAULT_TIMEOUT = 0.5           # Setting a default value 500 milliseconds of timeout  (in order to identify loss in Go-Back-N approach).
WINDOW_SIZE = 3                 # Setting fixed window size of 3 packets for Go-Back-N approach: the sender can send up to three packets before needing an acknowledgment from the receiver.
CHUNK_SIZE = 994                # This sets the size of each chunk of data that will be read from the file and sent over the network. In this case, each chunk is 994 bytes. The total packet size is: header (12 bytes) + message (994 bytes) = 1006 bytes. But we reserve only 6 bytes for the header. 

# Header size. 
# More about it: Python 3.12.3 documentation. struct — Interpret bytes as packed binary data: https://docs.python.org/3/library/struct.html
                # Islam S. (2024). Header. https://github.com/safiqul/2410/blob/main/header/header.py
HEADER_FORMAT = '!HHH'      #'!' - for network byte order. H indicates unsigned short integer, each 2 bytes in size. 
                            # Therefore, the total header length is:  3 integers × 2 bytes = 6 bytes
                            # Source: Islam S. (2024). Header. https://github.com/safiqul/2410/blob/main/header/header.py

# Flag masks. These flags are used to control the state and actions of the communication protocol in the code. They are represented as binary values, which makes it easy to combine multiple flags using bitwise operations.
# Kurose & Ross(2017) underlines impotance of the flags, and, particularly, ACK in GBN, as a reliable data transfer mechanism (pp. 221-226, 231-232). 
FIN_FLAG = 0b0001               # It signals that the sender has finished sending data. It is typically used in the connection teardown phase to gracefully close a connection.  
ACK_FLAG = 0b0010               # It indicates that the sender is acknowledging the successful reception of data.
SYN_FLAG = 0b0100               # Synchronize flag is used to initiate a connection. It is typically part of the connection establishment phase.
RES_FLAG = 0b0000               # Reserved flag is set to zero and is not currently used. It is a placeholder for potential future use or to ensure that the bit field has a consistent length.

# To prepare data to be sent over the network. 
# The code reads data in chunks of 994 bytes, adds a custom DRTP header of 6 bytes ( which consists of sequence number, acknowldgement number and flags), and then sends the data over UDP. 
def create_packet(seq, ack, flags, data):              # This function ensures that each packet has a header containing crucial information (sequence number, acknowledgment number, and flags) needed for reliable communication, followed by the actual data to be transmitted. 
    # Such approach helps in maintaining the integrity and order of the transmitted data, managing connections, and ensuring successful data transfer.
    # A sequence number (seq) is for ordering packets and detecting lost or out-of-order packets. Afterwards, the receiver can reassemble the original message in the correct order.
    # Acknowledgment Number (ack) acknowledge receipt of packets. It identifies that packet was successfully transmitted to the sender.
    # Control Flags (flags) shows the state of the connection. They help in managing the connection setup, data transfer, and connection teardown phases. 
    # data - the actual message data being transmitted (application data). 
    header = pack(HEADER_FORMAT, seq, ack, flags)       # The pack function is used to convert the sequence number, acknowledgment number, and flags into a binary format according to HEADER_FORMAT.
                                                        # The header is created as a binary string that combines the sequence number, acknowledgment number, and flags.
    packet = header + data                              # The binary header is concatenated with the data payload to form the complete packet.                        
    return packet                                       # The function returns the complete packet, which can now be sent over the network using a socket.

def parse_header(header):                               # This function is used to extract information (the sequence number, acknowledgment number, and flags) from the header of a received packet. This information are necessary for further protocol's operations.
    return unpack(HEADER_FORMAT, header)                # The unpack function from the struct module is used to convert the binary header back into its original components (sequence number, acknowledgment number, and flags).    
                                                        # Source: Python 3.12.3 documentation (2024). struct — Interpret bytes as packed binary data. https://docs.python.org/3/library/struct.html

# The send_ack function creates an acknowledgment packet and then sends it to the server using a UDP socket. 
# This is crucial for protocols that require reliable delivery and acknowledgment of received packets. 
def send_ack(client_socket, server_ip, server_port, seq_num, ack_num, flags):
    # client_socket: The socket object used for sending the ACK packet. In other words, it represents the connection through which data is sent.
    # server_ip: The IP address of the server to which the ACK packet is sent.
    # server_port: The port number of the server to which the ACK packet is sent.
    # seq_num: The sequence number to include in the ACK packet's header. This may not be particularly relevant for a pure acknowledgment packet but is included for consistency.
    # ack_num: The acknowledgment number to include in the ACK packet's header. This indicates the next expected sequence number from the sender, effectively acknowledging receipt of all prior packets.
    # flags: Control flags for the packet. As a rule, this will include the ACK flag to indicate that the packet is an acknowledgment.
    ack_packet = create_packet(seq_num, ack_num, flags, b'')                    # Creating the ACK Packet: the create_packet function is called with such arguments, as the sequence number, acknowledgment number, flags, and an empty byte string (b'').
                                                                                # As a result, ack_packet contains a properly formatted header with no additional data.
    client_socket.sendto(ack_packet, (server_ip, server_port))                  # For transmition the acknowledgment packet over the network to the server: the sendto method of the socket object is used to send the ack_packet to the specified server IP and port.
                                                                                # Source: Python 3.12.3 documentation (2024). socket — Low-level networking interface. https://docs.python.org/3/library/socket.html

# The GetChunk function reads a specific chunk of data from a file based on a given position and chunk size. 
# It positions the file pointer to the correct byte offset and reads the specified number of bytes, returning this chunk of data. 
# This function is useful for handling large files by breaking them into smaller parts for processing or transmission.
def GetChunk(file, pos, maxSize):                   
    # file: The file object to read from. This should be an open file object, typically opened in binary mode ('rb').
    # pos: The position in the file from which to start reading. This is specified in terms of chunks, not bytes. 
    # maxSize: This determines the size of the chunk to read (which is CHUNK_SIZE) from the file starting at the specified position.
    # For example, if pos is 2 and maxSize is 1024 bytes, the function will read from the 2048th byte of the file.
    file.seek(pos * maxSize)                # The seek method moves the file's read/write pointer to the position specified by pos * maxSize.
                                            # pos is the chunk index. Thus, pos * maxSize calculates the byte position in the file.
    chunk = file.read(maxSize)              # The read method reads maxSize bytes from the current position of the file pointer (in other words, from the file starting at the position specified by seek). 
    return chunk                            # Returns the data chunk that was read from the file.

# The GetTotalSize function helps to retrieve the total size of a file on the disk. 
# This is useful in various scenarios, such as when we need to check the size of files before performing certain operations on them.
def GetTotalSize(filename):                 # filename: The name of the file, which size we want to know. This should be a string representing the path to the file.
    return os.path.getsize(filename)        # The os.path.getsize function retrieves and returns the size of the file in bytes.
                                            # Source: Python 3.12.3 documentation (2024). os.path — Common pathname manipulations. https://docs.python.org/3/library/os.path.html

# The GetTotalChunks function calculates the total number of chunks needed to represent a file of a given size when each chunk has a maximum size limit. 
# This function is useful in scenarios where files need to be processed or transmitted in smaller, manageable parts.
def GetTotalChunks(fileSize, maxSize):
    # fileSize: The total size of the file in bytes that needs to be divided into chunks.
    # maxSize: The maximum size limit for each chunk in bytes. 
    return math.ceil(fileSize / maxSize)                # By dividing the file size by the maximum chunk size and rounding up the result, it ensures that the entire file is divided into complete chunks. 
    # The math.ceil function is used to round up the result of the division operation to the nearest integer. 
    # This ensures that even if there's a remainder after division, a complete chunk is allocated for the remaining bytes.
    # Source: Python 3.12.3 documentation (2024). math — Mathematical functions. https://docs.python.org/3/library/math.html

########################################################################################################################################################################################################
# This block of code represents the client-side logic for sending a file over a network using the UDP protocol, specifically implementing a Go-Back-N (GBN) protocol for reliable data transfer. 
def send_file(filename, server_ip, server_port, windowSize):                        # In the send_file function, chunks of the file are read and sent in a loop.
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)                # A UDP socket is created to establish communication with the server.
    client_socket.settimeout(DEFAULT_TIMEOUT)                                       # Timeout for socket operations is set using the settimeout method. Source: Python 3.12.3 documentation (2024). socket — Low-level networking interface. https://docs.python.org/3/library/socket.html
    
    window_size = WINDOW_SIZE if windowSize == None else windowSize                 # Initializing the window_size variable. If windowSize is None, it sets window_size to a default value WINDOW_SIZE. 
                                                                                    # Otherwise, it uses the provided windowSize value.
    file = None                             # Initializing the file variable to None to ensure that the file variable is defined before entering the try block.
    try:
        Log("Connection Establishment Phase: ")
        client_socket.sendto(create_packet(1, 0, SYN_FLAG, b''), (server_ip, server_port))      # A SYN packet is sent to initiate the connection establishment process. 
                                                                                                # The create_packet function constructs a packet with sequence number 1, acknowledgment number 0, SYN flag, and an empty message body.
                                                                                                # client_socket.sendto(..., (server_ip, server_port)) sends the packet to the server at the specified IP and port.
        Log("\nSYN packet is sent ")
        
        # Receiving SYN-ACK packet.
        syn_ack, _ = client_socket.recvfrom(1024)                   # The client waits to receive a SYN-ACK packet from the server. Theoretically, it receives up to 1024 bytes of data from server.
                                                                    # In practice, client will recieve 6 bytes packet, because the server sends only ACK packets with 6 bytes header.
        syn_ack_header = parse_header(syn_ack)                      # parse_header(syn_ack) extracts the header information from the received packet.
        Log ("SYN-ACK packet is recieved ")
        
        if syn_ack_header[2]:                                       # Checks if the SYN flag is set in the header of the received SYN-ACK packet.   
                                                                    # syn_ack_header[2] refers to the flags field in the parsed header.          
            send_ack(client_socket, server_ip, server_port, 0, syn_ack_header[0] + 1, ACK_FLAG)          # Sending an ACK packet to acknowledge the SYN-ACK packet.
            # send_ack() constructs and sends an ACK packet with sequence number 0, acknowledgment number syn_ack_header[0] + 1, and ACK flag.
            Log("ACK packet is sent \nConnection established \n" )
            client_socket.settimeout(0.5)                           # Setting a shorter timeout (0.5 seconds) for subsequent socket operations. This is useful for detecting timeouts quickly during data transfer. 
        # Handling Failed Connection Establishment.
        else:
            Log("Failed to establish connection in client ")        # If the SYN flag is not set in the received SYN-ACK packet, logs that the connection establishment failed and exits the function.
            return
    
        # Data Transfer Phase (Go-Back-N)
        Log("Data Transfer:  \n")
        
        file_size = GetTotalSize(filename)                  # The total size of the file is determined using the GetTotalSize function with the filename as its argument.
        maxChunks = GetTotalChunks(file_size, CHUNK_SIZE)   # A variable maxChunks calculates the total number of chunks that the file will be divided into for transmission.
        client_socket.sendto(create_packet(0, maxChunks, ACK_FLAG, b''), (server_ip, server_port))           # client_socket.sendto(..., (server_ip, server_port)) sends the constructed packet to the server at the specified IP and port.
            # For the packet: 
            # 0: Sequence number; set to 0 since the initial packet being sent. 
            # file_size: to inform the server how much data to expect.
            # ACK_FLAG: the packet is an acknowledgment packet.
            # b'': An empty byte string, indicating that this packet does not carry any application data.
        
        ack, _ = client_socket.recvfrom(1024)               # The client socket waits for ACK packet from the server. 
        # Theoretically, it receives up to 1024 bytes of data from the server, but practically it will recieve from the server an ACK packet with 6 byte header.
        ack_header = parse_header(ack)                      # It extracts relevant information from the header of the received packet.
        file = open(filename, '+rb')                        # opens the file in read-binary mode ('rb'), allowing the file to be read in binary format.
                                                            # The '+' indicates that the file is opened for both reading and writing (although writing is not necessary here).

        # Initialize Sliding Window Variables.
        base = 0                    # Variables base and next_seq_num are related to managing the sliding window. base with value of 0 represents the lowest sequence number of the unacknowledged packets in the sliding window.
        next_seq_num = 1            # 1 represents the sequence number of the next packet to be sent. 
        packets_in_flight = []      # packets_in_flight is initialized as an empty list for tracking the sequence numbers of packets that have been sent but not yet acknowledged.   

        # Data Transfer Phase (Sending File Chunks). The file is read and divided into chunks, which are sent to the server in a loop.
        while base <= maxChunks:                                                                # The loop continues until all chunks of the file have been sent and acknowledged.
            # base is the starting point of the sliding window, and maxChunks is the total number of chunks.
            while len(packets_in_flight) < window_size and next_seq_num <= maxChunks:           # The inner loop continues while the number of packets in flight (sent packets, which have not been yet acknowledged)
                                                                                                # is less than the window size and there are still chunks to send.
                
                chunk = GetChunk(file, next_seq_num - 1, CHUNK_SIZE)                             # The GetChunk() function is used to read each chunk of the file starting at the byte offset (next_seq_num - 1) * CHUNK_SIZE, and reads CHUNK_SIZE bytes of data.
                # This mechanism allows the file to be divided into manageable chunks for transmission, ensuring that each part of the file is read and sent in order.
                now = datetime.now()                                        # datetime.now() gets the current time for logging purposes. Source: Python 3.12.3 documentation (2024). datetime — Basic date and time types. https://docs.python.org/3/library/datetime.html
                client_socket.sendto(create_packet(next_seq_num, 0, 0, chunk), (server_ip, server_port))  #  Sending the chunk to the server.
                packets_in_flight.append(next_seq_num)                      # The sequence number of the sent packet is added to packets_in_flight.
                Log(f"{now.strftime('%H:%M:%S.%f')} -- packet with seq = {next_seq_num} is sent, sliding window = {packets_in_flight}")
                next_seq_num += 1                                           # next_seq_num is incremented to prepare for the next packet.

            # Handling Acknowledgments and Retransmissions. 
            try:
                # Receiving Acknowledgment.
                ack, _ = client_socket.recvfrom(1024)                   # The client waits to receive acknowledgments (ACKs) from the server for the packets it sends.
                ack_header = parse_header(ack)                          # Parsing the received packet's header to extract relevant information.
                # Processing Acknowledgment.
                if ack_header[2] & ACK_FLAG:                            #  Checking if the received packet is an acknowledgment packet by performing a bitwise AND operation with ACK_FLAG.
                    '''
                    If acknowladge id are not first item in array packets_in_flight
                    we must clear all  packets_in_flight and resend them.
                    '''
                    if len(packets_in_flight) > 0 and ack_header[1] == packets_in_flight[0] :       # Checking if the received acknowledgment corresponds to the first packet in packets_in_flight.
                        now = datetime.now()                            # datetime.now() gets the current time for logging purposes.
                        Log(f"{now.strftime('%H:%M:%S.%f')} -- ACK for packet = {ack_header[1]} is received")
                        # If the received acknowledgment corresponds to the first packet in packets_in_flight,
                        # the sequence number is removed from packets_in_flight.
                        packets_in_flight.remove(ack_header[1])                                      
                        base = ack_header[1] + 1                        # base is updated to the next expected sequence number.
            except  socket.timeout:                                     # If an acknowledgment is not received within the timeout period, packets are retransmitted.
                now = datetime.now()                                    # datetime.now() gets the current time for logging purposes.
                Log("Timeout occurred. Retransmitting...")
                Log('')
                Log(f"{now.strftime('%H:%M:%S.%f')} -- packet with seq = {packets_in_flight[0]} is retransmitted")
                Log('')
                packets_in_flight.clear()                               # Clearing the list of packets in flight.
                client_socket.settimeout(0.5)                           # Resetting the socket timeout.
                next_seq_num = base                                     # next_seq_num is reset to base to retransmit from the base of the sliding window.

        Log(".... \n DATA Finished \n \n")
    
    except FileNotFoundError:                           # Error handling is implemented to handle exceptions: the specified file does not exist.
        Log(f"File '{filename}' not found.")
    
 
    finally:                                            # This block is executed no matter what happens in the try block, ensuring that cleanup operations are performed.
        # Connection Teardown Phase.
        Log("\nConnection Teardown: \n")
        
        # Send FIN packet
        Log("FIN packet is sent ")                      # Indicating the end of the transmission.
        client_socket.sendto(create_packet(0, 0, FIN_FLAG, b''), (server_ip, server_port))          # Once all data has been sent, a FIN packet is sent to the server to initiate the termination of the connection.
        # The packet has a sequence number of 0, acknowledgment number of 0, and the FIN_FLAG set.
        
       # Handling Connection Teardown Response.
        fin_ack, _ = client_socket.recvfrom(1024)           # The client waits to receive a FIN-ACK packet from the server to confirm the termination. The server sends this packet to acknowledge the receipt of the FIN packet.
        fin_ack_header = parse_header(fin_ack)              # Parsing the header of the received FIN-ACK packet to extract the relevant information.
        if fin_ack_header[2] & ACK_FLAG:                    # Checking if the ACK_FLAG is set in the received packet. This confirms that the server has acknowledged the FIN packet.
            Log("FIN-ACK packet is received ")
            
            # Send ACK packet to acknowledge the FIN-ACK packet
            send_ack(client_socket, server_ip, server_port, 0, fin_ack_header[0] + 1, ACK_FLAG)     # Sending an ACK packet to the server to acknowledge the receipt of the FIN-ACK packet. 
            Log("Connection Closes \n")
        else:
            Log("Failed to close connection \n")

        file.close()                    # Closing the file that was being read.
        client_socket.close()           # Closing the UDP socket used for communication.
    Log('QUIT')                         # It logs that the file transfer process is complete and the program is quitting. This log is important for function RunLog.
      
########################################################################################################################################################################################################      
# FOR SERVER side.
transfer_lock = threading.Lock()                                # Lock for file transfer synchronization
'''In a multithreaded server application, multiple threads may try to read from or write to a shared resource simultaneously. 
Without proper synchronization, this can lead to race conditions, where the outcome depends on the sequence or timing of the threads' execution.
The lock ensures that only one thread can execute a critical section of code at a time.
Source: Python 3.12.3 documentation (2024). threading — Thread-based parallelism. https://docs.python.org/3/library/threading.html
'''
# The pack_header function creates a packet header by combining the sequence number, acknowledgment number, and flags into a binary format.
def pack_header(seq_num, ack_num, flags):                    
    return pack(HEADER_FORMAT, seq_num, ack_num, flags)         # The struct.pack method is used to pack (HEADER_FORMAT, seq_num, ack_num, flags) into a binary string according to the specified HEADER_FORMAT.

def send_ack_server(server_socket, client_address, seq_num, ack_num, flags):        # Sending an acknowledgment (ACK) packet from the server to a client.
    # server_socket: The socket object used by the server to send the packet.
    # client_address: The address of the client to which the ACK packet is sent.
    # seq_num: The sequence number of the ACK packet.
    # ack_num: The acknowledgment number of the ACK packet.
    # flags: The control flags for the ACK packet.
    ack_packet = pack_header(seq_num, ack_num, flags)               # Creating the ACK packet header.
    server_socket.sendto(ack_packet, client_address)                # Sending the packet to the client's address using the server socket.

# Performing a logical check on sequence numbers.
def IsNotRaisedPacket(prevSeqNumber, currSeqNumber):                # Checking whether the current packet's sequence number (currSeqNumber) is the immediate successor to the previous packet's sequence number (prevSeqNumber). 
                                                                    # This is often used in protocols that require packets to be processed in a specific order.
    # prevSeqNumber: The previous sequence number.
    # currSeqNumber: The current sequence number.
    return prevSeqNumber == None or prevSeqNumber + 1 == currSeqNumber          # Logical OR (or): If either condition is True, the entire expression evaluates to True.
    # If prevSeqNumber is None, the function returns True, indicating that the current packet is not out of order. None typically indicates absence of previous packet, implying this is the first packet being processed.
    # prevSeqNumber + 1 calculates the expected next sequence number. If currSeqNumber matches this expected next sequence number, the function returns True. It means that the packets are in the correct sequence.
    '''By using this function, a program can effectively manage and verify the order of packets in a communication sequence, 
    ensuring data integrity and proper reassembly of the transmitted information.
    '''

def MakeFile(filename):                         # Thie function creates a new file or truncates an existing file to zero length. This ensures that the file is ready to receive new data, effectively starting with an empty file.
    with open(filename, 'wb') as file:          # Openning the file in binary write mode. The with statement ensures proper resource management: It handles the file opening /closing automatically, even if an error occurs. 
                                                # This helps prevent resource leaks (e.g., file handles remaining open).
        file.close()                            # I added this line to be sure that the file will be closed. Including file.close() here is not harmful but unnecessary due to the context manager with.

# This function provides the necessary setup for a server to receive a file over a network, including ensuring that the file is ready to be written to and the server is ready to receive data.
def receive_file(filename, port, discard):
    # filename: The name of the file to be created or truncated, where the received data will be saved.
    # port: The port number on which the server will listen for incoming UDP packets.
    # discard: It could be used for conditional logic related to discarding packets or handling errors.
    global transfer_lock                                # This global varialbe is used elsewhere in the code to synchronize file transfers, ensuring that multiple threads or processes do not interfere with each other.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)            # Setting Up a UDP Server: Creating a UDP socket. This socket will be used to receive data packets from clients.
    server_socket.bind(('', port))                  # Binding the socket to the specified port number on all available network interfaces ('' indicates all interfaces). Listenning for incoming UDP packets on the specified port.
    Log("Server is listening... \n")
    
    MakeFile(filename)                              # Ensuring that any existing file with the specified name is cleared or a new file is created, ready to store incoming data.
    file = None                                     # This variable will be used later to reference the file object for writing the received data.
    

    
    while server_socket != None:                     # This loop continues as long as the server_socket object is not None, implying that the server is running and capable of receiving packets.
        # Receiving SYN packet. Start of the initial phase of three-way handshake process, where the server acknowledges the client's request to establish a connection. 
        syn_packet, client_address = server_socket.recvfrom(1024)       # The server waits to receive a SYN packet from the client using the recvfrom method of the socket object. 
                                                                        # Source: Python 3.12.3 documentation (2024). socket — Low-level networking interface. https://docs.python.org/3/library/socket.html
        # The received packet and the client's address are stored in syn_packet and client_address, respectively.
        syn_header = parse_header(syn_packet)                           # The header of the received packet is parsed using the parse_header function to extract relevant information.
        
        # Checking SYN Flag.
        if syn_header[2] & SYN_FLAG:                                    # Checking whether the third element of the header (representing flags) has the SYN flag set. AND operation with SYN_FLAG ensures that the SYN flag is set.
            Log("SYN packet is received ")
            
            # Sending SYN-ACK packet. If the SYN flag is set in the received packet, the server responds by sending a SYN-ACK packet to the client.
            server_socket.sendto(pack_header(1, syn_header[0] + 1, SYN_FLAG | ACK_FLAG), client_address)
            # The pack_header function is used to create the header for the SYN-ACK packet, with appropriate sequence and acknowledgment numbers, as well as flags indicating SYN and ACK.
            Log("SYN-ACK packet is sent ")
            
            # Receiving ACK packet. After sending the SYN-ACK packet, the server waits to receive an ACK packet from the client.
            ack_packet, _ = server_socket.recvfrom(1024)            # The received packet and its header are stored in ack_packet and ack_header, respectively.
            ack_header = parse_header(ack_packet)
            
            ''' Next part of the code marks the end of the initial phase of the three-way handshake process, confirming the establishment of the connection between the server and the client. 
            It prepares the server to start receiving data from the client and handles the necessary file operations for storing the received data.
            '''
            if ack_header[2] & ACK_FLAG:                    # Checking if the third element of the acknowledgment packet's header (representing flags) has the ACK flag set. A bitwise AND operation with the ACK_FLAG constant helps here.
            # If the ACK flag is set, it indicates that the client has acknowledged the server's SYN-ACK packet, confirming the establishment of the connection.
                Log("ACK packet is received ")              # Upon receiving the ACK packet with the ACK flag set, the server logs that the ACK packet is received.
                Log("Connection established ")              # The server confirms that the connection is established.
                
                file = open(filename, '+ab')                # The server opens the file specified by filename in append and binary mode ('ab'). This mode allows the server to write data to the file while preserving existing data.
                                                            # The file object is stored in the variable file, ready to receive incoming data from the client.
                # Starting receiving file.
                start_time = time.time()                    # start_time is set to the current time. This variable will be used to calculate the duration of the file transfer process.
                received_data = 0                           # 0 indicats that no data has been received yet.
                seq_num = 1                                 # 1 represents the sequence number of the first data packet expected from the client.
                previousSeqNumber = 0                       # 0 indicats that no previous sequence number has been received yet.
                
                # The continuous reception and processing of data packets from the client by the server.
                # Acquiring lock for file transfer.
                with transfer_lock:                         # Ensuring that only one thread can execute this block of code at a time. This is essential for maintaining consistency while writing data to the file.
                    # Continuous Reception data packets from the client.
                    while True:                                                              #  On the server side, the received data packets are processed, and the chunks of data are written to the file.
                        try:
                            data_packet, _ = server_socket.recvfrom(1024)                   # Receiving a data packet of up to 1024 bytes theoretically, because it will be up to 1000 bytes in practice (6 bytes header + 994 bytes of data chubk).
                            # Header Processing.
                            if len(data_packet) >= 6:                                      # Checking if the received data packet has at least 6 bytes, which is the size of the header.
                                header = data_packet[:6]
                                # If the packet is long enough, the header is extracted from the data packet.
                                header_seq_num, ack, flags = parse_header(header)           # The parse_header function parses its components (header_seq_num, ack, flags). 
                                                                                            # The header_seq_num variable holds the sequence number from the received header.
                                # Data Extraction.
                                data = data_packet[6:]                                     # If the data packet is of sufficient length, the data portion is extracted from the packet (data_packet[6:]), excluding the header.
                                # Continue processing the header and data.
                            else:                                                           # Handle the case when data_packet doesn't have enough bytes.
                                Log("Error: Data packet is too short")                      # Error Handling. If the received data packet is shorter than 6 bytes, it's considered an error. 

                            # If FIN flag is set, to end connection.
                            if header_seq_num == 0 and FIN_FLAG in header:                  # FIN Flag Checking. If the received packet has a sequence number of 0 and the FIN flag is set in the header, it indicates a termination request from the client.
                                Log("... \n\nFIN packet is received ")                      # The server logs the reception of the FIN packet. 
                                break                                                       # The server breaks out of the loop, ending the connection.
                            
                            # Discard Checking.
                            if discard != None and discard == header_seq_num:               # For case when the discard parameter is not None (the server is instructed to discard a specific packet) and the sequence number of the current packet matches the one to be discarded.
                                discard = None                                              # The server skips processing this packet. 
                                continue                                                    # The server continues to receive the next packet.
                            
                            now = datetime.now()                                            # It indiciates the current timestamp for using in the further log about the reception of the packet.
                            Log(f"{now.strftime('%H:%M:%S.%f')} -- packet {header_seq_num} is received")
                            
                            # Writing data to file.
                            if IsNotRaisedPacket(previousSeqNumber, header_seq_num):        # For case when the received packet's sequence number is the next expected one (determined by comparing with previousSeqNumber).
                                file.write(data)                                            # The data is written to the file.
                                previousSeqNumber = header_seq_num                          # The previousSeqNumber updates to the sequence number of the received packet.

                            '''
                                In this case we got correct packet number
                                Otherwice don't send anything
                            '''
                             # Sending ACK packet (for Sliding window).
                            if previousSeqNumber == header_seq_num:                         # If the received packet's sequence number matches the expected sequence number (previousSeqNumber),
                                send_ack_server(server_socket, client_address, 0, header_seq_num, ACK_FLAG)     # An ACK packet is sent back to the client to acknowledge the receipt of the data packet.
                            
                            # Updating received data size.
                            # The total size of received data (received_data) and the sequence number (seq_num) are updated to keep track of the progress of data reception.
                            received_data += len(data)
                            seq_num += 1
                            
                            # If a timeout occurs during the reception process (indicating no data has been received for a certain period), 
                            # the server logs a message indicating the timeout and breaks out of the loop, terminating the reception process.
                        except socket.timeout:
                            Log("Timeout occurred")
                            break
                
                # Sending FIN-ACK Packet.
                # After receiving the FIN packet from the client and processing it, the server sends a FIN-ACK packet back to acknowledge the termination request. 
                # This packet has the ACK and FIN flags set, indicating acknowledgment of the FIN packet and signaling the server's intent to terminate the connection.
                server_socket.sendto(pack_header(1, 0, FIN_FLAG | ACK_FLAG), client_address)
                Log("FIN ACK packet is sent \n")
                
                # Calculating throughput and connection closure.
                # 
                end_time = time.time()
                duration = end_time - start_time
                throughput = (received_data * 8) / (duration * 1024 * 1024)                 # Calculation of the throughput of the file transfer process by dividing the total amount of data received (in bits) by the duration of the transfer (in seconds). 
                                                                                            # Converting the result to megabits per second (Mbps). 
                Log(f"\nThe throughput is {throughput:.2f} Mbps")                           # Loging of information about throughput for monitoring purposes.
                Log("Connection Closes ")
                file.close()                                                                # The file is closed.
            else:
                Log("Failed to establish connection")
                return
         
            # Socket Deinitialization. 
            server_socket = None                # None helps to break out of the while loop, effectively deinitializing the socket and ending the server's listening process.
    Log('QUIT')                                 # It indicates the end of the server-side operation. This log is important for function RunLog.


######################################################################################################################################################################################################## 

# This section of the code defines a logging mechanism using threads to handle concurrent logging operations. 
threads = []                                    # The threads list is initialized to store thread objects.

# Logging Queue and Lock.
logInQ = []                         # An empty list used as a queue to store log messages.
logLock = threading.Lock()          # A threading lock used to synchronize access to the logging queue. Source: Python 3.12.3 documentation (2024). threading — Thread-based parallelism. https://docs.python.org/3/library/threading.htm

# Adding log messages to the logging queue (logInQ).
# The Log function acquires the lock before appending the data to the queue and releases the lock afterward to ensure thread safety.
def Log(data):
    logLock.acquire()
    logInQ.append(data)
    logLock.release()

# Logging Thread.
# Function RunLog is designed to be executed by a separate thread to continuously process and print log messages from the logging queue.
def RunLog():
    while True:                         # The function runs indefinitely, continuously processing log messages until it receives a termination signal.
        # Thread Synchronization.
        logLock.acquire()               # For ensuring thread safety while accessing the logging queue.
        logOutQ = logInQ.copy()         # After acquiring the lock, the function makes a copy of the logging queue (logInQ) to avoid potential issues with concurrent modification.
        logInQ.clear()                  # Once the copy is made, the original logging queue is cleared to prepare for new log messages.
        logLock.release()               # Releasing the lock to allow other threads to access the logging queue.
        # Processing Log Messages.
        for data in logOutQ:            # Iteration over the copied log messages (logOutQ).
            if data == 'QUIT':          # If a log message is 'QUIT', indicating the termination of the logging process, the function returns, effectively ending the thread.
                return                  
            print(data)                 # Otherwise, it prints each log message to the console.
        # Sleep Interval. 
        time.sleep(0.2)                 # After processing all log messages, the function sleeps for a short duration (0.2 seconds). This sleep interval helps prevent the thread from consuming excessive CPU resources while waiting for new log messages to arrive.


# Function RunServer sets up the server functionality by starting two threads: one for receiving files and another for logging. 
# This concurrent execution enables the server to handle file reception while simultaneously logging activities in real-time.
def RunServer(args):
    receive_thread = threading.Thread(target=receive_file, args=(args.filename, args.port, args.discard))
    # A thread is created with the target function set to receive_file, which handles the reception of files. It's passed arguments such as the filename, port, and discard flag from the args object.
    log_thread = threading.Thread(target=RunLog)        # Another thread is created with the target function set to RunLog, which continuously processes and prints log messages.
    
    # Both threads are started using the start() method. This initiates the execution of the target functions (receive_file and RunLog) in separate threads concurrently with the main thread.
    receive_thread.start()
    log_thread.start()
    
    # Thread Management. References to both threads (receive_thread and log_thread) are appended to the threads list. 
    # This allows for the tracking of active threads and potentially joining them later to ensure proper termination.
    threads.append(receive_thread)
    threads.append(log_thread)


# RunClient sets up the client functionality by starting two threads: one for sending files and another for logging. 
# This concurrent execution enables the client to send files while simultaneously logging activities in real-time.
# This function is somewhat similar to the RunServer function, but is applied on the client side.
def RunClient(args):
    # Thread Initialization. 
    send_thread = threading.Thread(target=send_file, args=(args.filename, args.ip, args.port, args.window))
    # A thread is created with the target function set to send_file, which handles the sending of files. It's passed arguments such as the filename, IP address, port, and window size from the args object.
    log_thread = threading.Thread(target=RunLog)                    # It continuously processes and prints log messages.
    
    # Thread Start. log_thread is started before send_thread using the start() method. This ensures that log messages are processed and printed concurrently with the file sending operation.
    log_thread.start()
    send_thread.start()
    
    # Thread Management.References to both threads (send_thread and log_thread) are appended to the threads list. 
    threads.append(send_thread)
    threads.append(log_thread)

def JoinAll():                          # JoinAll function is responsible for joining all active threads created in the application, ensuring that the program waits for their completion before proceeding further. 
    for thread in threads:              # The code iterates over each thread in the threads list.
        if thread.is_alive():           # For each thread, it checks if the thread is still alive using the is_alive() method. Source: Python 3.12.3 documentation (2024). threading — Thread-based parallelism. https://docs.python.org/3/library/threading.htm
            thread.join()               # If the thread is alive, it waits for the thread to complete its execution by calling the join() method. This effectively blocks the program's execution until the thread finishes.
    threads.clear()                     # After joining all threads, the threads list is cleared, indicating that all threads have been properly handled.
    
    
    # main function is the entry point of the script and helps to run the server and client modes of the DRTP/UDP File Sender application.
def main():             
    parser = argparse.ArgumentParser(description="DRTP/UDP File Sender")                                # The argparse module facilitates command-line argument parsing.                       
    # Sources: Islam S. (2024). Argparse-and-oop: https://github.com/safiqul/2410/tree/main/argparse-and-oop
    # Python 3.12.3 documentation: argparse — Parser for command-line options, arguments and sub-commands: https://docs.python.org/3/library/argparse.html
    # This setup allows users to specify various parameters when running the script.
    parser.add_argument("-s", "--server", action='store_true', help="run in server mode")               # The action='store_true' parameter indicates that if this argument is provided, its value should be set to True.              
    parser.add_argument("-c", "--client", action='store_true', help="run in client mode")               # The help parameter provides a brief description of what the argument does.       
    parser.add_argument("-f", "--filename", required=True, help="Name of the file to send")             # The required=True parameter ensures that this argument must be provided by the user.              
    parser.add_argument("-i", "--ip", required=True, help="Server IP address")
    parser.add_argument("-p", "--port", type=int, required=True, help="Server port number")             # The type=int parameter ensures that the provided value is parsed as an integer.
    parser.add_argument("-w", "--window", type=int, required = False, help="Client window size")        # The required=False parameter makes this argument optional.
    parser.add_argument("-d", "--discard", type=int, required = False, help="discard on server side one time")
    args = parser.parse_args()
    
    # Based on the arguments provided, the code determines whether the script should run in server mode, client mode, or both.
    if args.server:             # If the --server flag is provided, it calls the RunServer function.
        RunServer(args)
    elif args.client:           # If the --client flag is provided, it calls the RunClient function.
        RunClient(args)
    else:                       # If neither flag (-s or -c) is provided, it defaults to running both server and client modes.
        RunServer(args)
        RunClient(args)

    # After starting the server and client threads (if applicable), it calls the JoinAll function to wait for all threads to finish execution.
    JoinAll()                               # The JoinAll function ensures proper synchronization by joining all active threads before allowing the program to exit.
    # Waiting for threads to finish.

if __name__ == "__main__":          # The main() function is invoked when the script is executed. It checks if the script is being run directly (__name__ == "__main__") and then calls the main() function.
    main()