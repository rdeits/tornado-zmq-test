using HttpServer
using WebSockets
using ZMQ

function handle_file_request(req, res)
    @show req.resource
    if req.resource == "/static/"
        open("test.html") do file
            return Response(read(file))
        end
    else
        return Response(404)
    end
end

function run_server()
    connections = Set{WebSocket}()

    websocket_handler = WebSocketHandler() do req, client
        @show client
        push!(connections, client)
        try
            while true
                read(client)
            end
        catch e
            if e isa WebSockets.WebSocketClosedError
                if client in connections
                    delete!(connections, client)
                end
            end
        end
    end

    server = Server(HttpHandler(handle_file_request),
                    websocket_handler)
    yield()

    context = Context()
    socket = Socket(context, REP)
    ZMQ.bind(socket, "tcp://*:5555")

    @async run(server, 8888)
    while true
        msg = take!(convert(IOStream, ZMQ.recv(socket)))
        @show msg
        for connection in connections
            write(connection, msg)
        end
        ZMQ.send(socket, "ok")
    end
end

run_server()





