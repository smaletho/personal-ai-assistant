import React from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import {
  Box,
  Flex,
  VStack,
  Link,
  Icon,
  useColorModeValue,
} from '@chakra-ui/react';
import { ChatIcon, CalendarIcon, CheckIcon, SettingsIcon } from '@chakra-ui/icons';

const NavItem = ({ icon, children, path }) => {
  const location = useLocation();
  const isActive = location.pathname === path;
  const activeColor = useColorModeValue('brand.600', 'brand.200');
  const activeBg = useColorModeValue('gray.100', 'gray.700');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');
  
  return (
    <Link
      as={RouterLink}
      to={path}
      style={{ textDecoration: 'none' }}
      _focus={{ boxShadow: 'none' }}
      width="100%"
    >
      <Flex
        align="center"
        p="4"
        mx="4"
        borderRadius="lg"
        role="group"
        cursor="pointer"
        bg={isActive ? activeBg : 'transparent'}
        color={isActive ? activeColor : ''}
        _hover={{
          bg: hoverBg,
        }}
      >
        {icon && (
          <Icon
            mr="4"
            fontSize="16"
            as={icon}
            color={isActive ? activeColor : 'gray.500'}
          />
        )}
        {children}
      </Flex>
    </Link>
  );
};

const Sidebar = () => {
  const bg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Box
      as="nav"
      pos="sticky"
      top="0"
      h="calc(100vh - 60px)"
      borderRight="1px"
      borderRightColor={borderColor}
      bg={bg}
      w={{ base: 'full', md: 60 }}
      display={{ base: 'none', md: 'block' }}
    >
      <VStack align="stretch" spacing={0} mt={4}>
        <NavItem icon={ChatIcon} path="/">
          Chat
        </NavItem>
        <NavItem icon={CalendarIcon} path="/calendar">
          Calendar
        </NavItem>
        <NavItem icon={CheckIcon} path="/tasks">
          Tasks
        </NavItem>
        <NavItem icon={SettingsIcon} path="/settings">
          Settings
        </NavItem>
      </VStack>
    </Box>
  );
};

export default Sidebar;
