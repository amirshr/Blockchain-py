from functools import reduce
import json
from hash_util import hash_block
from block import Block
from transaction import Transaction
from verification import Verification
import requests

MINING_REWARD = 10


class Blockchain:
    def __init__(self, public_key, node_id):
        self.__open_transactions = []
        self.genesis_block = Block(0, '', [], 100, 0)
        self.__chain = [self.genesis_block]
        self.public_key = public_key
        self.__peer_nodes = set()
        self.node_id = node_id
        self.load_data()

    @property
    def chain(self):
        return self.__chain[:]

    @chain.setter
    def chain(self, value):
        self.__chain = value

    def get_open_transactions(self):
        return self.__open_transactions[:]

    def load_data(self):
        try:
            with open('blockchain-{}.txt'.format(self.node_id), mode='r') as f:
                file_content = f.readlines()
                block__chain = json.loads(file_content[0][:-1])
                updated_blockchain = []
                for block in block__chain:
                    converted_tx = [Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in
                                    block['transactions']]
                    updated_block = Block(block['index'], block['previous_hash'], converted_tx, block['proof'],
                                          block['timestamp'])
                    updated_blockchain.append(updated_block)
                    self.chain = updated_blockchain
                open_transactions = json.loads(file_content[1][:-1])
                updated_transactions = []
                for tx in open_transactions:
                    updated_transaction = Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount'])
                    updated_transactions.append(updated_transaction)
                self.__open_transactions = updated_transactions
                peer_nodes = json.loads(file_content[2])
                for peer_node in peer_nodes:
                    self.__peer_nodes.add(peer_node)
        except (IOError, IndexError):
            pass

    def save_data(self):
        try:
            with open('blockchain-{}.txt'.format(self.node_id), mode='w') as f:

                savable_chain = [block.__dict__ for block in
                                 [Block(index=block_el.index, previous_hash=block_el.previous_hash,
                                        transactions=[tx.__dict__ for tx in block_el.transactions],
                                        proof=block_el.proof,
                                        timestamp=block_el.timestamp) for block_el in self.__chain]]
                savable_transaction = [transaction.__dict__ for transaction in self.__open_transactions]
                f.write(json.dumps(savable_chain))
                f.write('\n')
                f.write(json.dumps(savable_transaction))
                f.write('\n')
                f.write(json.dumps(list(self.__peer_nodes)))
        except IOError:
            print('Saving failed!')

    def proof_of_work(self):
        last_block = self.__chain[-1]
        last_hash = hash_block(last_block)
        proof = 0
        while not Verification.valid_proof(self.__open_transactions, last_hash, proof):
            proof += 1
        return proof

    def get_balance(self, sender=None):
        if sender is None:
            if self.public_key is None:
                return None
            participant = self.public_key
        else:
            participant = sender
        tx_sender = [[tx.amount for tx in block.transactions if tx.sender == participant] for block in self.__chain]
        open_tx_sender = [tx.amount for tx in self.__open_transactions if tx.sender == participant]
        tx_sender.append(open_tx_sender)
        amount_sent = reduce(lambda tx_sum, tx_amt:
                             tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum + 0, tx_sender, 0)
        tx_recipient = [[tx.amount for tx in block.transactions
                         if tx.recipient == participant] for block in self.__chain]
        amount_received = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum + 0,
                                 tx_recipient, 0)
        return amount_received - amount_sent

    def get_last_block__chain_value(self):
        if len(self.__chain) < 1:
            return None
        return self.__chain[-1]

    def add_transaction(self, sender, recipient, signature, amount=1, is_receiving=False):
        transaction = Transaction(sender, recipient, signature, amount)
        if Verification().checking_transaction(transaction=transaction, get_balance=self.get_balance):
            self.__open_transactions.append(transaction)
            self.save_data()
            if not is_receiving:
                for node in self.__peer_nodes:
                    url = 'http://{}/broadcast-transaction'.format(node)
                    try:
                        response = requests.post(url, json={
                            'sender': sender,
                            'recipient': recipient,
                            'signature': signature,
                            'amount': amount
                        })
                        if response.status_code == 400 or response.status_code == 500:
                            print('Transaction declined, needs resolving')
                            return False
                    except requests.ConnectionError:
                        continue
            return True
        return False

    def add_block(self, block):
        transactions = [Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in
                        block['transactions']]
        proof_is_valid = Verification.valid_proof(transactions[:-1], block['previous_hash'], block['proof'])
        hashes_match = hash_block(self.chain[-1]) == block['previous_hash']
        if not proof_is_valid or not hashes_match:
            return False
        converted_block = Block(block['index'], block['previous_hash'], transactions, block['proof'],
                                block['timestamp'])
        self.__chain.append(converted_block)
        self.save_data()
        stored_transactions = self.__open_transactions[:]
        for itx in block['transactions']:
            for opentx in stored_transactions:
                if opentx.sender == itx['sender'] and opentx.recipient == itx['recipient'] and\
                        opentx.amount == itx['amount'] and opentx.signature == itx['signature']:
                    try:
                        self.__open_transactions.remove(opentx)
                    except ValueError:
                        print('Item was already removed')

        return True

    def mine_block(self):
        if self.public_key is None:
            return None
        hashed_block = hash_block(self.__chain[-1])
        proof = self.proof_of_work()
        reward_transaction = Transaction('MINING', self.public_key, '', MINING_REWARD)
        copied_transactions = self.get_open_transactions()
        for tx in copied_transactions:
            if not Verification.verify_transaction(tx):
                return None
        copied_transactions.append(reward_transaction)
        block = Block(index=len(self.__chain), previous_hash=hashed_block, transactions=copied_transactions,
                      proof=proof)
        self.__chain.append(block)
        self.__open_transactions = []
        self.save_data()
        for node in self.__peer_nodes:
            converted_block = block.__dict__.copy()
            converted_block['transactions'] = [tx.__dict__ for tx in converted_block['transactions']]
            url = 'http://{}/broadcast-block'.format(node)
            try:
                response = requests.post(url, json={'block': converted_block})
                if response.status_code == 500 or response.status_code == 400:
                    print('Block declined, need resolving')
            except requests.ConnectionError:
                continue
        return block

    def add_peer_node(self, node):
        self.__peer_nodes.add(node)
        self.save_data()

    def remove_peer_node(self, node):
        self.__peer_nodes.discard(node)
        self.save_data()

    def get_peer_nodes(self):
        return list(self.__peer_nodes)[:]
