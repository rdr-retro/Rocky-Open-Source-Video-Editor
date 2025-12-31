#!/bin/bash
# Compilar todo el proyecto Rocky Open Source Video Editor incluyendo las librerías JavaCV
javac -cp "lib/*:." a/visor/*.java a/mastersound/*.java b/timeline/*.java c/toolbar/*.java egine/media/*.java egine/engine/*.java egine/render/*.java egine/persistence/*.java MainAB.java
