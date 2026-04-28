"use client";

import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { MessageSquare, BarChart3, ArrowRight } from "lucide-react";

export default function HomePage(): JSX.Element {
  return (
    <div className="relative flex min-h-[85vh] flex-col items-center justify-center overflow-hidden">
      {/* Background glowing orb - Calm & Cooling */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-100 blur-3xl opacity-60 mix-blend-multiply animate-pulse-slow"></div>

      <motion.div 
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="z-10 text-center"
      >
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="mx-auto mb-6"
        >
          <Image
            src="/logo.png"
            alt="DeBias Logo"
            width={80}
            height={80}
            className="drop-shadow-xl"
            priority
          />
        </motion.div>
        
        <h1 className="mb-4 bg-gradient-to-br from-slate-700 to-slate-400 bg-clip-text text-5xl font-extrabold tracking-tight text-transparent sm:text-6xl">
          DeBias
        </h1>
        <p className="mx-auto mb-10 max-w-2xl text-lg text-slate-500">
          Bias-mitigated chat interface with live fairness monitoring. Stream responses in real-time while analyzing toxicity, stereotypes, and disparity signals.
        </p>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.8, ease: "easeOut" }}
        className="z-10 grid w-full max-w-4xl grid-cols-1 gap-6 sm:grid-cols-2"
      >
        <Link href="/chat" className="group relative block h-full">
          <div className="absolute -inset-0.5 rounded-3xl bg-gradient-to-r from-sky-300 to-blue-200 opacity-0 blur transition duration-500 group-hover:opacity-50"></div>
          <div className="glass shadow-glass hover:shadow-glass-hover animate-float relative flex h-full flex-col items-start rounded-3xl p-8 transition-all duration-300 group-hover:-translate-y-2">
            <div className="mb-6 rounded-xl bg-sky-100 p-4 text-sky-600">
              <MessageSquare size={28} />
            </div>
            <h2 className="mb-3 text-2xl font-bold text-slate-800">Live Chat</h2>
            <p className="mb-8 text-slate-500">Interact with the bias-mitigated AI in real-time with streaming responses and confidence intervals.</p>
            <div className="mt-auto flex items-center font-semibold text-sky-600 transition-transform group-hover:translate-x-2">
              Start chatting <ArrowRight className="ml-2" size={18} />
            </div>
          </div>
        </Link>

        <Link href="/dashboard" className="group relative block h-full">
          <div className="absolute -inset-0.5 rounded-3xl bg-gradient-to-r from-teal-300 to-cyan-200 opacity-0 blur transition duration-500 group-hover:opacity-50"></div>
          <div className="glass shadow-glass hover:shadow-glass-hover animate-float relative flex h-full flex-col items-start rounded-3xl p-8 transition-all duration-300 group-hover:-translate-y-2" style={{ animationDelay: '0.2s' }}>
            <div className="mb-6 rounded-xl bg-teal-50 p-4 text-teal-600">
              <BarChart3 size={28} />
            </div>
            <h2 className="mb-3 text-2xl font-bold text-slate-800">Fairness Dashboard</h2>
            <p className="mb-8 text-slate-500">Monitor demographic disparities, toxicity scores, and refusal rates across live conversations.</p>
            <div className="mt-auto flex items-center font-semibold text-teal-600 transition-transform group-hover:translate-x-2">
              View metrics <ArrowRight className="ml-2" size={18} />
            </div>
          </div>
        </Link>
      </motion.div>
    </div>
  );
}
