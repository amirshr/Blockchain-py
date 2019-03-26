from functools import reduce
import json
from hash_util import hash_block
from block import Block
from transaction import Transaction
from verification import Verification

MINING_REWARD = 10


class Blockchain:
    def __init__(self, hosting_node_id):
        self.__open_transactions = []
        genesis_block = Block(0, '', [], 100, 0)
        self.__chain = [genesis_block]
        self.load_data()
        self.hosting_node_id = hosting_node_id

    @property
    def chain(self):
        return self.__chain[:]

    @chain.setter
    def chain(self, val):
        self.__chain = val

    def get_open_transactions(self):
        return self.__open_transactions[:]

    def load_data(self):
        try:
            with open('block__chain.txt', mode='r') as f:
                file_content = f.readlines()
                block__chain = json.loads(file_content[0][:-1])
                updated_blockchain = []
                for block in block__chain:
                    converted_tx = [Transaction(tx['sender'], tx['recipient'], tx['amount']) for tx in
                                    block['transactions']]
                    updated_block = Block(block['index'], block['previous_hash'], converted_tx, block['proof'],
                                          block['timestamp'])
                    updated_blockchain.append(updated_block)
                    self.chain = updated_blockchain
                open_transactions = json.loads(file_content[1])
                updated_transactions = []
                for tx in open_transactions:
                    updated_transaction = Transaction(tx['sender'], tx['recipient'], tx['amount'])
                    updated_transactions.append(updated_transaction)
                self.__open_transactions = updated_transactions
        except (IOError, IndexError):
            pass

    def save_data(self):
        try:
            with open('block__chain.txt', mode='w') as f:

                savable___chain = [block.__dict__ for block in
                                   [Block(index=block_el.index, previous_hash=block_el.previous_hash,
                                          transactions=[tx.__dict__ for tx in block_el.transactions],
                                          proof=block_el.proof,
                                          timestamp=block_el.timestamp) for block_el in self.__chain]]
                savable_transaction = [transaction.__dict__ for transaction in self.__open_transactions]
                f.write(json.dumps(savable___chain))
                f.write('\n')
                f.write(json.dumps(savable_transaction))
        except IOError:
            print('Saving failed!')

    def proof_of_work(self):
        last_block = self.__chain[-1]
        last_hash = hash_block(last_block)
        proof = 0
        while not Verification.valid_proof(self.__open_transactions, last_hash, proof):
            proof += 1
        return proof

    def get_balance(self):
        tx_sender = [[tx.amount for tx in block.transactions if tx.sender == self.hosting_node_id]
                     for block in self.__chain]

        open_tx_sender = [tx.amount for tx in self.__open_transactions if tx.sender == self.hosting_node_id]
        tx_sender.append(open_tx_sender)
        amount_sent = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum, tx_sender, 0)

        tx_recipient = [[tx.amount for tx in block.transactions if tx.recipient == self.hosting_node_id]
                        for block in self.__chain]
        amount_received = reduce(
            lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum, tx_recipient, 0)
        return amount_received - amount_sent

    def get_last_block__chain_value(self):
        if len(self.__chain) < 1:
            return None
        return self.__chain[-1]

    def add_transaction(self, recipient, sender, amount=1):
        transaction = Transaction(sender, recipient, amount)
        if Verification.verify_transaction(transaction, self.get_balance):
            self.__open_transactions.append(transaction)
            self.save_data()
            return True
        return False

    def mine_block(self):
        last_block = self.__chain[-1]
        hashed_block = hash_block(last_block)
        proof = self.proof_of_work()
        reward_transaction = Transaction('MINING', self.hosting_node_id, MINING_REWARD)
        copied_transactions = self.__open_transactions[:]
        copied_transactions.append(reward_transaction)
        block = Block(index=len(self.__chain), previous_hash=hashed_block, transactions=copied_transactions,
                      proof=proof)
        self.__chain.append(block)
        self.__open_transactions = []
        self.save_data()
        return True
