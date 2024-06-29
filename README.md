# Assignment in Networking and Cloud Computing.
##  Implementation of a file transfer application (DRTP/UDP protocol).

## Overview
The objective is to develop and analyze a Python-based file transfer application enabling seamless data exchange between clients and servers using DRTP (Datagram Reliable Transfer Protocol) over UDP. The application operates by reading data in 994-byte chunks, appending a custom 6-byte DRTP header, and transmitting the data via UDP. File operations are conducted in binary mode (rb and wb), utilizing the struct package for header manipulation. Although the application supports concurrent transfer of two source files (multithreading), it restricts operations to allow only one transfer at a time.
DRTP (Datagram Reliable Transfer Protocol) is a protocol designed to ensure reliable data transfer over unreliable networks, such as UDP. 
Implementing DRTP involves adding layers of logic on top of UDP to enhance reliability. Techniques include:
1) **Acknowledgment and Retransmission**: The sender awaits acknowledgments from the receiver after transmitting each packet. If no acknowledgment is received within a specified timeout, the sender retransmits the packet.
2) **Sequencing**: Each packet is assigned a sequence number to guarantee correct delivery order at the receiver's end.
3) **Flow Control**: The sender adjusts the data transmission rate based on feedback from the receiver, preventing data overload.
Theoretical points about the reliable data transfer could be found in Kurose & Ross, 2017 (pp. 206-226).
The client reads a file from the local system and transmits it over DRTP/UDP, specifying the file name, server address, and port number via command line arguments. Reliability on UDP is ensured through acknowledgment and retransmission logic, incorporating a default timeout of 500ms via socket.settimeout().
A file transfer server receives files from clients over UDP and saves them to the file system. Additionally, it tracks data received from connected clients, calculating and displaying throughput based on received data and connection duration. The server's port number matches that of the client. Upon file reception, the server opens the file in binary mode for writing.

## Dependencies
This code relies on the following Python libraries: socket (for network communication), argparse (for parsing command-line arguments), os (for interacting with the operating system, used for file operations), time (for timing-related functionality), math (for mathematical operations), threading (for concurrent execution of tasks), datetime (for manipulating dates and times). No external dependencies are required beyond the standard Python library.
Installation: No installation is required, except of Python 3.x.

## Variables
Below are represented variables, which play crucial roles in various aspects of running the code, including network communication, file transfer, and synchronization between threads.
`DEFAULT_TIMEOUT`: Timeout duration in seconds for socket operations.
`WINDOW_SIZE`: Fixed window size for Go-Back-N protocol.
`CHUNK_SIZE`: Size of data chunks read from the file.
`HEADER_FORMAT`: Format string for packing/unpacking packet headers.
`FIN_FLAG`, `ACK_FLAG`, `SYN_FLAG`, `RES_FLAG`: Flag masks for packet flags.
`transfer_lock`: Thread lock for file transfer synchronization.
`logInQ`: Queue for logging messages.
`logLock`: Thread lock for accessing the logging queue.
`threads`: List to store references to active threads.
`server_socket`: Socket object for the server-side communication.
`discard`: Variable to discard a specific packet on the server-side.
`syn_packet`: Received SYN packet from the client.
`syn_header`: Parsed header of the received SYN packet.
`ack_packet`: ACK packet sent by the server.
`ack_header`: Parsed header of the received ACK packet.
`file`: File object for reading/writing data.
`start_time`: Start time of file transfer.
`received_data`: Total size of received data.
`seq_num`: Sequence number for packet ordering.
`previousSeqNumber`: Sequence number of the previously received packet.

## Functions
The core logic and operations of the DRTP/UDP file sender application are encapsulated in the following functions.
`create_packet(seq, ack, flags, data)`: Creates a packet with specified sequence number, acknowledgment number, flags, and data.
`parse_header(header)`: Parses the header of a packet and returns the sequence number, acknowledgment number, and flags.
`send_ack(client_socket, server_ip, server_port, seq_num, ack_num, flags)`: Sends an acknowledgment packet with specified sequence number, acknowledgment number, and flags.
`GetChunk(file, pos, maxSize)`: Reads a chunk of data from the file starting from the specified position.
`GetTotalSize(filename)`: Returns the total size of the file specified by the filename.
`GetTotalChunks(fileSize, maxSize)`: Calculates the total number of chunks required to transfer a file of the given size with the specified maximum chunk size.
`send_file(filename, server_ip, server_port, windowSize)`: Establishes a connection with the server and sends the specified file using the Go-Back-N protocol.
`pack_header(seq_num, ack_num, flags)`: Packs the sequence number, acknowledgment number, and flags into a header for packet transmission.
`send_ack_server(server_socket, client_address, seq_num, ack_num, flags)`: Sends an acknowledgment packet from the server to the client with specified sequence number, acknowledgment number, and flags.
`IsNotRaisedPacket(prevSeqNumber, currSeqNumber)`: Checks if the current packet's sequence number is the expected next sequence number.
`MakeFile(filename)`: Creates or clears the contents of a file with the specified filename.
`receive_file(filename, port, discard)`: Listens for incoming connections, receives files from clients, and saves them to the specified filename.
`Log(data)`: Logs the specified data for debugging purposes.
`RunLog()`: Runs a continuous loop to process and print log messages.
`RunServer(args)`: Sets up and runs the server-side functionality based on the provided command-line arguments.
`RunClient(args)`: Sets up and runs the client-side functionality based on the provided command-line arguments.
`JoinAll()`: Waits for all threads to finish execution before exiting.
`main()`: Entry point of the script; parses command-line arguments and initiates server or client functionality accordingly.

## Functionality
The code implements a DRTP/UDP file sender application capable of efficient and reliable file transmission over UDP (User Datagram Protocol) utilizing the Go-Back-N protocol. Key functionalities include:
**Client-Server Communication:** Facilitates communication between client and server over UDP sockets, enabling file transfer.
**Go-Back-N Protocol:** Implements the Go-Back-N protocol for reliable data transmission, ensuring ordered delivery of packets and handling packet loss.
**File Transfer:** Enables the transfer of files between client and server, handling file segmentation, transmission, and reassembly at the destination.
**Error Handling:** Implements robust error handling mechanisms to address potential issues such as socket timeouts, file not found errors, and network disruptions.
**Concurrency:** Utilizes multithreading to support concurrent execution of tasks, enhancing performance and scalability.

## Exception Handling
The code incorporates robust exception handling to gracefully manage potential errors and ensure smooth execution even in challenging scenarios. Key aspects of exception handling include:
***Socket Timeout Handling***: Timely detection and handling of socket timeouts to prevent communication disruptions, ensuring reliable data transmission.
***File Not Found Handling***: Graceful handling of file not found errors, providing informative messages to users and preventing unexpected termination.
***Error Logging***: Comprehensive logging of errors and exceptions, enabling effective debugging and troubleshooting during application development and deployment.
***Connection Teardown***: Proper teardown of connections, including sending FIN packets and handling acknowledgments, to ensure orderly closure and release of resources.
***Thread Synchronization***: Synchronization of concurrent threads through locks to prevent race conditions and maintain data integrity in multi-threaded environments.

## Usage
**Client** 
To initiate file transmission from the client side, use the following command:  `python3 application.py -c -f <filename> -i <server_ip_address> -p <server_port>`
Replace <filename> with the name of the file you wish to send, <server_ip_address> with the IP address of the server, and <server_port> with the port number the server is listening on.
Example: `python3 application.py -c -f Photo.jpg -i 10.0.1.2 -p 8080`
**Server** 
To receive files on the server side, execute the following command: `python3 application.py -s -f <filename_to_save> -i <server_ip_address> -p <port>`
Replace <filename_to_save> with the name to save the received file, <server_ip_address> with the IP address of the server, and <port> with the port number the server is listening on.
Example: `python3 application.py -s -f received_file.jpg -i 10.0.1.2 -p 8080`


## Mininet Testing

**Code Testing in Mininet with simple-topo.py**
1) ***Network Topology Construction:*** Construct the network topology in Mininet with `sudo python3 simpletopo.py` and use the `dump` command to gather essential data about h1 as the client, h2 as the server, and r as the router. File simple-topo.py could be taken from: Islam S. (2024). simple-topo.py. https://github.com/safiqul/2410/blob/main/mininet/simple-topo.py
2) ***Terminal Launching:*** Employ the `xterm h1, h2, r` command to launch separate terminals for the client, server, and router.
3) ***Server Configuration:***  Configure h2 to operate in server mode with help of file application.py and prepare it for receiving files using the following command: `python3 application.py -s -f received_file.jpg -i <server_ip_address> -p <server_port>`
4) ***Packet Capture:*** Initiate the `tcpdump` command on the router r to record data in the Wireshark .pcap file.
5) ***Program Execution:*** Ran the program on the client side (h1) using: `python3 application.py -c -f photo.jpg -i <server_ip_address> -p <server_port>`
6) ***Analysis:*** 
Upon completion of the program execution, terminate the tcpdump process on r using the combination of keys: `ctrl and c`.
Verify that the records of running "application.py" on h1 (client) and h2 (server) sides appear appropriate.
Observe that the copied picture "received_file.jpg" closely resembles the original "photo.jpg", with similar technical features observed.
You could also analyse the Wireshark file, which captures the establishment of connections, data transfer processes, and connection closures, providing a detailed record of network activity.

**Task 1: Executing File Transfer with Different Window Sizes**
To evaluate the performance of the file transfer application with varying window sizes (3, 5, and 10) and calculate throughput values, follow these steps:
***Window Size of 3:*** By default, the window size is set to 3 in the application.py script, and the server calculates throughput automatically. Review the throughput value displayed in the server terminal.
***Window Size of 5/ 10:*** To obtain the throughput value for a window size of 5 or 10, add the `-w 5` or `-w 10` flag to both the client and server commands.
Example: 
`python3 application.py -c -w 5 -f photo.jpg -i 10.0.1.2 -p 3544` (for client).
`python3 application.py -s -w 5 -f 2.jpg -i 10.0.1.2 -p 3544` (for server).

**Task 2: Testing with Modified RTT and Window Sizes**
***Modification of RTT in simple-topo.py:*** 
Before constructing topology in Mininet, open the simple-topo.py file. Replace the value of 100ms with either 50ms or 200ms in line 43: `net["r"].cmd("tc qdisc add dev r-eth1 root netem delay 100ms")`
(Source: Islam S.(2024). Instruction for Individual Assignment). Construct the topology and run application.py in Mininet, as described in Task 1 above. 

**Task 3: Dropping File Test** 
For testing purposes with the `-d flag`, you can simulate dropping a file during transmission. 
Example: 
- for client: `python3 application.py -c -f Photo.jpg -i 10.0.1.2 -p 8080`
- for server: `python3 application.py -s -i 10.0.1.2 -p 8080 -d 8`
In this example, the server will drop the packet with sequence number 8.

**Task 4: Testing with Simulated Packet Loss**
***Modify simple-topo.py with 2% loss:*** Open the simple-topo.py file. Comment out line #43: `# net["r"].cmd("tc qdisc add dev r-eth1 root netem delay 100ms")`
Uncomment line #44: `net["r"].cmd("tc qdisc add dev r-eth1 root netem delay 100ms loss 2%")` (Source: Islam S. (2024). Instruction for Individual Assignment).
Execute the file transfer application as described above with desired parameters. 
For applying 5% loss, change the number 2% to 5% in the newly uncommented line 44. 
