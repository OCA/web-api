from threading import Thread

from lxml import etree
from werkzeug.serving import make_server
from werkzeug.wrappers import Request, Response


class SoapTestServer:
    def __init__(self, wsdl_path):
        self.wsdl = open(wsdl_path).read()
        self.app = self.create_app()
        self.server = None
        self.thread = None
        self.url = None

    def create_app(self):
        def application(environ, start_response):
            request = Request(environ)
            if request.path == "/SayHello/":
                root = etree.fromstring(request.data)
                name = root.xpath("//firstName/text()")[0]
                response_xml = (
                    """
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Body>
        <ns1:sayHelloResponse xmlns:ns1="urn:examples:helloservice">
            <greeting>Hello %s!</greeting>
        </ns1:sayHelloResponse>
    </soapenv:Body>
</soapenv:Envelope>
                    """
                    % name
                )
                response = Response(response_xml, mimetype="text/xml")
                return response(environ, start_response)

            return Response("Not Found", status=404)(environ, start_response)

        return application

    def start(self, port=80):
        self.server = make_server("localhost", port, self.app)
        self.thread = Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        self.url = "http://localhost/hello.wsdl"

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.thread.join()
