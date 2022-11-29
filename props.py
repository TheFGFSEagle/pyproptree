#!/usr/bin/env python
#-*- coding:utf-8 -*-

import typing
from plum import dispatch

class Node:
	@dispatch
	def __init__(self):
		self._name = "/"
		self._parent = None
		self._children = []
		self._listeners = []
		self._attrs = {}
		self._value = None
		self._type = None
	
	def __repr__(self):
		return f"props.Node(path={self.getPath()})"
	
	def _getPathParts(self, path):
		parts = list(filter(None, path.split("/")))
		for i, part in enumerate(parts):
			if part == ".":
				parts[i] = ""
			elif part == "..":
				parts[i] = ""
				parts[i - 1] = ""
		return list(filter(None, parts))
	
	def _joinPathParts(self, parts):
		return "/".join(parts)
	
	def getRootNode(self):
		if self._parent:
			return self._parent.getRootNode()
		else:
			return self
	
	def getParent(self):
		return self._parent
	
	def getPath(self):
		if self._parent:
			ppath = self._parent.getPath()
			if ppath == "/":
				ppath += self._name
			else:
				ppath += "/" + self._name
			return ppath
		else:
			return "/"
	
	def getNode(self, path, create=False, index=0):
		parts = self._getPathParts(path)
		if parts == []:
			return self
		
		node = None
		for child in self._children:
			if child.getName() == parts[0]:
				node = child.getNode(self._joinPathParts(parts[1:]), create)
				break
		else:
			if create:
				child = Node()
				child._parent = self
				child.setName(parts[0])
				self._children.append(child)
				node = child.getNode(self._joinPathParts(parts[1:]), create)
		return node
	
	@overload
	def setType(self, type: typing.Callable):
		if self._type == type: return
		self._type = type
		self._value = self._type(self._value)
	
	@overload
	def setType(self, type: typing.Any):
		raise TypeError(f"type {type} for props.Node.setType is not callable")
	
	def setName(self, name):
		self._name = name
	
	def getName(self):
		return self._name
	
	@dispatch
	def getValue(self) -> str:
		return str(self._value)
	
	@dispatch
	def getValue(self) -> bool:
		if lower(self._value) == "false":
			return False
		elif lower(self._value) == "true":
			return True
		else:
			return bool(self._value)
	
	@dispatch
	def getValue(self) -> int:
		return int(self._value)
	
	@dispatch
	def getValue(self) -> float:
		return float(self._value)
	
	@dispatch	
	def getValue(self) -> typing.Any:
		return self._value
	
	@dispatch
	def setValue(self, value: typing.Union[str, bool, int, float]):
		self._value = value
	
	@dispatch
	def setValue(self, value: typing.Any):
		raise TypeError(f"cannot set value of node {self.getPath()} to {value} with type {type(value)}")
