import React from 'react';
import { 
  Box, 
  Flex, 
  Heading, 
  IconButton, 
  useColorMode, 
  useColorModeValue,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Avatar
} from '@chakra-ui/react';
import { SunIcon, MoonIcon } from '@chakra-ui/icons';

const Header = () => {
  const { colorMode, toggleColorMode } = useColorMode();
  const bg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Box 
      as="header" 
      position="sticky" 
      top={0} 
      zIndex={10} 
      bg={bg} 
      borderBottom="1px" 
      borderColor={borderColor}
      px={4}
      py={2}
      shadow="sm"
    >
      <Flex alignItems="center" justifyContent="space-between">
        <Flex alignItems="center">
          <Heading as="h1" size="md" letterSpacing="tight">
            AI Calendar Assistant
          </Heading>
        </Flex>
        
        <Flex alignItems="center">
          <IconButton
            aria-label="Toggle color mode"
            icon={colorMode === 'light' ? <MoonIcon /> : <SunIcon />}
            onClick={toggleColorMode}
            variant="ghost"
            mr={2}
          />
          
          <Menu>
            <MenuButton
              as={Avatar}
              size="sm"
              cursor="pointer"
              src="https://bit.ly/broken-link"
              name="User"
            />
            <MenuList>
              <MenuItem>Profile</MenuItem>
              <MenuItem>Settings</MenuItem>
              <MenuItem>Logout</MenuItem>
            </MenuList>
          </Menu>
        </Flex>
      </Flex>
    </Box>
  );
};

export default Header;
