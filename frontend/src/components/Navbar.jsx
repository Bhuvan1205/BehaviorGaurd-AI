import React from 'react';
import { Shield, Bell, User } from 'lucide-react';
import { Button } from './ui/button';

export function Navbar() {
  return (
    <nav className="h-16 border-b border-white/10 bg-black/40 backdrop-blur-xl supports-[backdrop-filter]:bg-black/20 fixed top-0 w-full z-40 flex items-center px-6 transition-all">
      <div className="flex items-center gap-3 font-bold text-lg text-primary tracking-tight">
        <div className="p-1.5 bg-primary/10 rounded-lg border border-primary/20 shadow-glow">
          <Shield className="w-5 h-5" />
        </div>
        <span>BehaviorGuard</span>
      </div>
      
      <div className="ml-auto flex items-center space-x-6">
        <Button variant="ghost" size="icon" className="relative hover:bg-white/5 rounded-full transition-all">
          <Bell className="h-5 w-5 text-muted-foreground hover:text-foreground transition-colors" />
          <span className="absolute top-2 right-2 flex h-2 w-2 rounded-full bg-destructive shadow-glow-danger"></span>
        </Button>
        <div className="h-6 w-px bg-white/10 hidden sm:block"></div>
        <Button variant="ghost" className="hidden sm:flex items-center gap-3 hover:bg-white/5 rounded-full px-3 transition-all">
          <div className="bg-gradient-to-tr from-primary/80 to-primary/20 p-1 rounded-full">
            <User className="h-4 w-4 text-black" />
          </div>
          <span className="text-sm font-medium text-foreground/80">Admin</span>
        </Button>
      </div>
    </nav>
  );
}
