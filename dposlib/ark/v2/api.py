# -*- coding: utf-8 -*-
# © Toons
# ~ https://docs.ark.io/api/public/v2/

import os
import dposlib

from dposlib import ldgr
from dposlib.util import misc
from dposlib.util.data import filter_dic, loadJson, dumpJson


class Wallet(dposlib.blockchain.Wallet):
	
	def __init__(self, address, **kw):
		dposlib.blockchain.Data.__init__(self, dposlib.rest.GET.api.wallets, address, **dict({"returnKey":"data"}, **kw))

	def getDelegate(self):
		return Delegate(self.username) if self.isDelegate else None

	def transactions(self, limit=50):
		sent = misc.loadPages(dposlib.rest.GET.api.wallets.__getattr__(self.address).__getattr__("transactions").__getattr__("sent"), limit=limit)
		received = misc.loadPages(dposlib.rest.GET.api.wallets.__getattr__(self.address).__getattr__("transactions").__getattr__("received"), limit=limit)
		return [filter_dic(dic) for dic in sorted(received+sent, key=lambda e:e.get("timestamp", {}).get("epoch"), reverse=True)][:limit]


class NanoS(dposlib.blockchain.NanoS):

	def __init__(self, network, account, index, **kw):
		# aip20 : https://github.com/ArkEcosystem/AIPs/issues/29
		self.derivationPath = "44'/%s'/%s'/%s'/%s" % (dposlib.rest.cfg.slip44, network, account, index)
		self.address = dposlib.core.crypto.getAddress(ldgr.getPublicKey(ldgr.parseBip32Path(self.derivationPath)))
		self.debug = kw.pop("debug", False)
		dposlib.blockchain.Data.__init__(self, dposlib.rest.GET.api.wallets, self.address, **dict({"returnKey":"data"}, **kw))

	@staticmethod
	def fromDerivationPath(derivationPath, **kw):
		nanos = NanoS(0,0,0, **kw)
		address = dposlib.core.crypto.getAddress(ldgr.getPublicKey(ldgr.parseBip32Path(derivationPath)))
		nanos.address = address
		nanos.derivationPath = derivationPath
		nanos._Data__args = (address,)
		nanos.update()
		return nanos


class Delegate(dposlib.blockchain.Data):

	def __init__(self, username, **kw):
		dposlib.blockchain.Data.__init__(self, dposlib.rest.GET.api.delegates, username, **dict({"returnKey":"data"}, **kw))

	def getWallet(self):
		return Wallet(self.address)

	def forged(self):
		return filter_dic(self._Data__dict["forged"])

	def voters(self):
		voters = misc.loadPages(dposlib.rest.GET.api.delegates.__getattr__(self.username).__getattr__("voters"))
		return list(sorted([filter_dic(dic) for dic in voters], key=lambda e:e["balance"], reverse=True))
	
	def lastBlocks(self, limit=50):
		return dposlib.rest.GET.api.delegates(self.username, "blocks", returnKey="data")[:limit]

	def lastBlock(self):
		if self.blocks.get("last", False):
			return Block(self.blocks["last"]["id"])


class Block(dposlib.blockchain.Data):

	def __init__(self, blk_id, **kw):
		dposlib.blockchain.Data.__init__(self, dposlib.rest.GET.api.blocks, blk_id, **dict({"returnKey":"data"}, **kw))

	def previous(self):
		return Block(self._Data__dict["previous"])

	def transactions(self):
		return dposlib.rest.GET.api.blocks(self.id, "transactions", returnKey="data")


class Webhook(dposlib.blockchain.Data):

	@staticmethod
	def create(peer, event, target, conditions):
		data = rest.POST.api.webhooks(peer=peer, event=event, target=target, conditions=conditions, returnKey="data")
		if "token" in data:
			dumpJson(data, os.path.join(dposlib.ROOT, ".webhooks", dposlib.rest.cfg.network, data["token"][32:]))
		return Webhook(data["id"], peer=peer)
		
	def __init__(self, whk_id, **kw):
		dposlib.blockchain.Data.__init__(self, dposlib.rest.GET.api.webhooks, "%s"%whk_id, **dict({"track":False, "returnKey":"data"}, **kw))

	def delete(self):
		rest.DELETE.api.webhooks("%s"%self.id, peer=self.__kwargs.get("peer", None))
		whk_path = os.path.join(dposlib.ROOT, ".webhooks", dposlib.rest.cfg.network, self.token[32:])
		if os.path.exists(whk_path):
			os.remove(whk_path)
