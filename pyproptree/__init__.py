#!/usr/bin/env python
#-*- coding:utf-8 -*-

import io
import os
import typing
import pathlib
from plum import dispatch
from lxml import etree

def countConsecutive(element, l: typing.Iterable, start: int = 0):
	if len(l) == 0 or start > len(l) - 1 or element not in l:
		return -1
	
	c = start
	while c + 1 < len(l) and l[c] == element and l[c + 1] == element:
		c += 1
	return  c - start

class NodePath:
	pass

class NodePathPart:
	pass

NodePathType = typing.Union[NodePath, str, NodePathPart, typing.Sequence[typing.Union[NodePathPart, str]]]

class NodePathPart:
	@dispatch
	def __init__(self, name: "NodePathPart", index: int):
		self.name = name.name
		self.index = index
	
	@dispatch
	def __init__(self, name: str, index: int):
		self.name = name
		self.index = index
	
	@dispatch
	def __init__(self, s: typing.Optional[str] = ""):
		self.name, self.index = self.splitNameIndex(s)
	
	@staticmethod
	def splitNameIndex(s):
		index = 0
		name = s
		if "[" in s and "]" in s:
			name, index = s.split("[")
			index = int(index.split("]")[0])
		return name, index
	
	@dispatch
	def __eq__(self, other: "NodePathPart"):
		return self.index == other.index and self.name == other.name
	
	@dispatch
	def __eq__(self, other: str):
		other = NodePathPart(other)
		return self == other
	
	@dispatch
	def __ne__(self, other: "NodePathPart"):
		return self.index != other.index or self.name != other.name
	
	@dispatch
	def __ne__(self, other: str):
		other = NodePathPart(other)
		return self != other
	
	def __bool__(self):
		return self.name not in ("", ".")
	
	def __repr__(self):
		return f"{self.name}[{self.index}]"
	
	def __str__(self):
		if self.index != 0:
			return repr(self)
		else:
			return str(self.name)

class NodePath:
	@dispatch
	def __init__(self, parts: typing.Optional[typing.Sequence[str]]=None):
		self.parts = map(NodePathPart, parts or [])
		self._filterPathParts()
	
	@dispatch
	def __init__(self, parts: typing.Optional[typing.Sequence[NodePathPart]]=None):
		self.parts = parts or []
		self._filterPathParts()
	
	@dispatch
	def __init__(self, path: typing.Optional[str]=None):
		self.parts = map(NodePathPart, (path or "").split("/"))
		self._filterPathParts()
	
	# copy constructor
	@dispatch
	def __init__(self, other: "NodePath"):
		self.parts = other.parts
		self._filterPathParts()
	
	def __repr__(self):
		return "/".join(map(repr, self.parts))
	
	def __str__(self):
		return "/".join(map(str, self.parts))
	
	def _filterPathParts(self):
		self.parts = list(self.parts)
		parts = []
		for i, part in enumerate(self.parts):
			if part:
				if len(self.parts) < i + 1 and self.parts[i + 1] == "..":
					self.parts[i + 1] = None
				else:
					parts.append(part)
		self.parts = parts
	
	@dispatch
	def __add__(self, other: typing.Sequence[typing.Union[NodePathPart, str]]) -> "NodePath":
		new = NodePath(self)
		new.parts += other
		new._filterPathParts()
		return new
	
	@dispatch
	def __add__(self, other: "NodePath") -> "NodePath":
		new = NodePath(self)
		new.parts += other.parts
		return new
	
	@dispatch
	def __iadd__(self, other: typing.Sequence[typing.Union[NodePathPart, str]]) -> "NodePath":
		self.parts += other
		self._filterPathParts()
		return self
	
	@dispatch
	def __iadd__(self, part: typing.Union[str, NodePathPart]) -> "NodePath":
		self.parts.append(part)
		self._filterPathParts()
		return self
	
	@dispatch
	def __iadd__(self, other: "NodePath") -> "NodePath":
		self.parts += other.parts
		return self
	
	@dispatch
	def __truediv__(self, other: NodePathType) -> "NodePath":
		return self.__iadd__(other)
	
	@dispatch
	def __itruediv__(self, other: NodePathType) -> "NodePath":
		return self.__iadd__(other)
	
	def __iter__(self) -> typing.Iterator["NodePath"]:
		return iter(self.parts)
	
	def __len__(self) -> int:
		return len(self.parts)
	
	@dispatch
	def __getitem__(self, index: slice) -> "NodePath":
		start, stop, _ = index.indices(len(self.parts))
		indices = range(start, stop, 1)
		return NodePath([self.parts[i] for i in indices])
	
	@dispatch
	def __getitem__(self, index: int) -> "NodePath":
		return self.parts[index]

class Node:
	@dispatch
	def __init__(self):
		self._name = "/"
		self._index = 0
		self._parent = None
		self._children = []
		self._listeners = []
		self._attrs = {}
		self._value = None
		self._type = None
		self._path = NodePath()
	
	def __repr__(self):
		return f"props.Node(path={repr(self.getPath())})"
	
	@dispatch
	def addNode(self, path: NodePathType, n: "Node"):
		path = NodePath(path)
		existing = self.getNode(path / n.getName(), False)
		if not existing:
			self._children.append(n)
		else:
			existing.addNodes("/", n.getChildren())
	
	@dispatch
	def addNodes(self, path: NodePathType, ns: typing.Iterable["Node"]):
		for n in ns:
			self.addNode(path, n)
	
	def hasChildren(self):
		return self.countChildren() > 0
	
	def countChildren(self, name: typing.Union[str, NodePathPart] = None):
		if name:
			c = 0
			for node in self.getChildren():
				if node.getName() == name:
					c += 1
			return c
		else:
			return len(self._children)
	
	def getChildren(self):
		return sorted(self._children, key=lambda c: c.getIndex())
	
	def getRootNode(self):
		if self._parent:
			return self._parent.getRootNode()
		else:
			return self
	
	def getParent(self):
		return self._parent
	
	def getPath(self) -> NodePath:
		if not self._parent:
			return NodePath("/")
		else:
			return self._parent.getPath() / NodePathPart(self.getName(), self.getIndex())
	
	def getPathString(self) -> str:
		return str(self.getPath())
	
	def getIndex(self) -> int:
		return self._index
	
	@dispatch
	def _findUnusedIndex(self, child: typing.Union[str, NodePathPart]):
		m = 0
		for c in self._children:
			if c.getName() == child:
				m = max(m, c.getIndex())
		return m
	
	@dispatch
	def getNode(self, path: NodePathType, create: bool=False):
		path = NodePath(path)
		if not len(path):
			return self
		elif countConsecutive("..", path, 0) > 0:
			print("Warning: attempting moving up in the property tree past the root node, returning the root node")
			return self.getRootNode()
		
		node = None
		for child in self._children:
			if child.getName() == path[0].name and child.getIndex() == path[0].index:
				if len(path) > 1:
					node = child.getNode(path[1:], create)
				else:
					node = child
				break
		
		if node == None:
			if create:
				child = Node()
				child._parent = self
				child.setName(path[0].name)
				child._index = path[0].index or self._findUnusedIndex(child.getName())
				self._children.append(child)
				if len(path) > 1:
					node = child.getNode(path[1:], create)
				else:
					node = child
		return node
	
	@dispatch
	def remove(self):
		self.getParent().remove(self.getPath()[-1])
	
	@dispatch
	def remove(self, path: NodePathType):
		if not len(path):
			self.remove()
		else:
			for c in self.getChildren():
				if c.getName() == path[0]:
					self._children.remove(c)
				break
	
	@dispatch
	def setType(self, type: typing.Callable):
		if self._type == type: return
		self._type = type
		self._value = self._type(self._value)
	
	@dispatch
	def setType(self, type: typing.Any):
		raise TypeError(f"type {type} for props.Node.setType is not callable")
	
	@dispatch
	def setName(self, name: typing.Union[str, NodePathPart]):
		self._name = NodePathPart(name)
	
	@dispatch
	def getName(self) -> NodePathPart:
		return self._name
	
	@dispatch
	def getNameString(self) -> str:
		return str(self._name)
	
	@dispatch
	def getStringValue(self) -> str:
		return str(self._value)
	
	@dispatch
	def getBoolValue(self) -> bool:
		if str(self._value).lower() == "false":
			return False
		elif str(self._value).lower() == "true":
			return True
		else:
			return bool(self._value)
	
	@dispatch
	def getIntValue(self) -> int:
		return int(self._value)
	
	@dispatch
	def getFloatValue(self) -> float:
		return float(self._value)
	
	@dispatch	
	def getValue(self) -> typing.Any:
		return self._value
	
	def setValue(self, value: typing.Any):
		if self.countChildren() != 0:
			raise TypeError("cannot set a value on a node that has children")
		
		try:
			self.value = self._type(value)
		except:
			raise ValueError("could not convert {value} to type {self._type} of node {self.getPathString()}")

class Tree:
	@dispatch
	def __init__(self):
		self.root = None
	
	@dispatch
	def __init__(self, root: Node):
		self.root = root
	
	def _xmlElementToNode(self, tree: etree.Element, root: Node = None):
		if not root:
			root = Node()
			root.setName(tree.tag)
		
		for element in tree:
			index = root.countChildren(element.tag)
			child = root.getNode(NodePath(f"{element.tag}[{index}]"), True)
			if not child.hasChildren():
				child.setValue(element.text)
				t = element.attribs.get("type", "string")
				if t == "string":
					child.setType()
			self._xmlElementToNode(element, child)
		
		return root
	
	@dispatch
	def loadLxmlElement(self, el: etree._Element):
		node = self._xmlElementToNode(el)
		if not self.root:
			self.root = node
		else:
			self.root.addNode("/", node)
	
	@dispatch
	def loadString(self, s: str):
		tree = etree.fromstring(s).getroot()
		self.loadLxmlElement(tree)
	
	@dispatch
	def loadFile(self, file: typing.Union[str, typing.IO]):
		tree = etree.parse(file).getroot()
		self.loadLxmlElement(tree)
	
	def _getNodesAsLxmlElement(self, element: etree._Element, node: Node):
		if not node.hasChildren():
			element.text = node.getStringValue()
			element.attribs["type"] = node.getType()
		else:
			for subnode in node.getChildren():
				subelement = etree.ElementBase()
				subelement.tag = subnode.getNameString()
				self._getNodesAsLxmlElement(subelement, subnode)
				element.append(subelement)
	
	def _getLxmlElementTree(self):
		if not self.root:
			return etree.ElementTree()
		
		rootelement = etree.ElementBase()
		rootelement.tag = self.root.getNameString()
		self._getNodesAsLxmlElement(rootelement, self.root)
		tree = etree.ElementTree(rootelement)
		return tree
	
	def toString(self, indent="\t"):
		if not self.root:
			return ""
		
		tree = self._getLxmlElementTree()
		etree.indent(tree, indentation=indent)
		return etree.tostring(tree, encoding="UTF-8", xml_declaration=True, pretty_print=True)
	
	def toDict(self, node: typing.Optional[Node] = None):
		if not self.root:
			return {}
		
		node = node or self.root
		d = {}
		if node.hasChildren():
			d[node.getName()] = []
			for c in node.getChildren():
				d[node.getName()].append(self.toDict(c))
		else:
			d[node.getName()] = node.getValue()
		return d
	
	@dispatch
	def toFile(self, path: str):
		os.makedirs(os.path.abspath(os.path.join(*os.path.split(path)[:-1])), exist_ok=True)
		
		with open(path, "wb") as f:
			f.write(self.toString())
	
	@dispatch
	def toFile(self, f: typing.BinaryIO):
		f.write(self.toString())

