from hash_util import hash_block, hash_string_256


class Verification:
    def __init__(self):

        pass

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

    @staticmethod
    def verify_transaction(transaction, get_balance):
        return get_balance() >= transaction.amount

    @classmethod
    def verify_transactions(cls, open_transactions, get_balance):
        return all([cls.verify_transaction(tx, get_balance) for tx in open_transactions])

    @staticmethod
    def valid_proof(transactions, last_hash, proof):
        guess = hash_string_256(
            (str([tx.to_ordered_dict() for tx in transactions]) + str(last_hash) + str(proof)).encode())
        return guess[0:2] == '00'
