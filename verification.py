from hash_util import hash_block, hash_string_256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
import binascii


class Verification:

    @classmethod
    def verify_chain(cls, blockchain):
        for (index, block) in enumerate(blockchain):
            if index == 0:
                continue
            if block.previous_hash != hash_block(blockchain[index - 1]):
                return False
            if not cls.valid_proof(block.transactions[:-1], block.previous_hash, block.proof):
                print('Proof of work is invalid')
                return False
        return True

    def checking_transaction(self, transaction, get_balance, check_funds=True):
        if check_funds:
            return get_balance() >= transaction.amount and self.verify_transaction(transaction)
        else:
            return self.verify_transaction(transaction)

    @classmethod
    def verify_transactions(cls, open_transactions, get_balance):
        return all([cls.checking_transaction(tx, get_balance, False) for tx in open_transactions])

    @staticmethod
    def valid_proof(transactions, last_hash, proof):
        guess = hash_string_256(
            (str([tx.to_ordered_dict() for tx in transactions]) + str(last_hash) + str(proof)).encode())
        return guess[0:2] == '00'

    @staticmethod
    def verify_transaction(transaction):
        public_key = RSA.importKey(binascii.unhexlify(transaction.sender))
        verifier = PKCS1_v1_5.new(public_key)
        h = SHA256.new((str(transaction.sender) + str(transaction.recipient) + str(transaction.amount)).encode('utf8'))
        return verifier.verify(h, binascii.unhexlify(transaction.signature))
