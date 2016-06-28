# Author: Hubert Kario, (c) 2015
# Released under Gnu GPL v2.0, see LICENSE file for details
"""Example MAC value fuzzer"""

from __future__ import print_function
import traceback
import sys

from tlsfuzzer.runner import Runner
from tlsfuzzer.messages import Connect, ClientHelloGenerator, \
        ClientKeyExchangeGenerator, ChangeCipherSpecGenerator, \
        FinishedGenerator, ApplicationDataGenerator, \
        fuzz_mac, fuzz_seal
from tlsfuzzer.expect import ExpectServerHello, ExpectCertificate, \
        ExpectServerHelloDone, ExpectChangeCipherSpec, ExpectFinished, \
        ExpectAlert, ExpectClose

from tlslite.constants import CipherSuite, AlertLevel, AlertDescription

def main():
    """check if incorrect MAC hash is rejected by server"""
    conversations = {}

    #aead = True # GCM
    aead = False # CBC

    for pos, val in [
                     (-1, 0x01),
                     (-1, 0xff),
                     (-2, 0x01),
                     (-2, 0xff),
                     (-6, 0x01),
                     (-6, 0xff),
                     (-12, 0x01),
                     (-12, 0xff),
                     (-20, 0x01),
                     (-20, 0xff),
                     # SHA-1 HMAC has just 20 bytes
                     ]:
        conversation = Connect("localhost", 4433)
        node = conversation
        suite = CipherSuite.TLS_RSA_WITH_AES_128_GCM_SHA256 if aead else \
                CipherSuite.TLS_RSA_WITH_AES_128_CBC_SHA
        ciphers = [suite, CipherSuite.TLS_EMPTY_RENEGOTIATION_INFO_SCSV]
        node = node.add_child(ClientHelloGenerator(ciphers))
        node = node.add_child(ExpectServerHello())
        node = node.add_child(ExpectCertificate())
        node = node.add_child(ExpectServerHelloDone())
        node = node.add_child(ClientKeyExchangeGenerator())
        node = node.add_child(ChangeCipherSpecGenerator())
        node = node.add_child(FinishedGenerator())
        node = node.add_child(ExpectChangeCipherSpec())
        node = node.add_child(ExpectFinished())
        node = node.add_child( \
            fuzz_seal(ApplicationDataGenerator( b"GET / HTTP/1.0\n\n"), xors={pos:val})
            if aead else
            fuzz_mac(ApplicationDataGenerator( b"GET / HTTP/1.0\n\n"), xors={pos:val})
            )
        node = node.add_child(ExpectAlert(AlertLevel.fatal,
                                          AlertDescription.bad_record_mac))
        node = node.add_child(ExpectClose())

        conversations["XOR position " + str(pos) + " with " + str(hex(val))] = \
                conversation

    # run the conversation
    good = 0
    bad = 0

    for conversation_name in conversations:
        conversation = conversations[conversation_name]

        print(conversation_name + "...")

        runner = Runner(conversation)

        res = True
        #because we don't want to abort the testing and we are reporting
        #the errors to the user, using a bare except is OK
        #pylint: disable=bare-except
        try:
            runner.run()
        except:
            print("Error while processing")
            print(traceback.format_exc())
            res = False
        #pylint: enable=bare-except

        if res:
            good+=1
            print("OK")
        else:
            bad+=1

    print("Test end")
    print("successful: {0}".format(good))
    print("failed: {0}".format(bad))

    if bad > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
