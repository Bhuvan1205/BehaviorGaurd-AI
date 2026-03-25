import React from 'react';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { motion, AnimatePresence } from 'framer-motion';
import { useLocation } from 'react-router-dom';

export function PageLayout({ children }) {
  const location = useLocation();
  const isAuthPage = location.pathname === '/login';

  if (isAuthPage) {
    return <div className="min-h-screen bg-background">{children}</div>;
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="flex">
        <Sidebar className="hidden md:flex" />
        <main className="flex-1 md:pl-64 pt-16 min-h-screen">
          <div className="p-8 max-w-7xl mx-auto">
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                {children}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}
